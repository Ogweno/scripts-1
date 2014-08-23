#! /usr/bin/env python

# Predict planetary visibility in the early evening (sunset to midnight),
# and upcoming conjunctions between two or more planets.
# Copyright 2014 Akkana Peck -- share and enjoy under the GPLv2 or later.

import ephem
import math

# How low can a planet be at sunset or midnight before it's not interesting?
min_alt = 10. * math.pi / 180.

# How close do two bodies have to be to consider it a conjunction?
max_sep = 3.5 * math.pi / 180.

sun = ephem.Sun()

planets = [
    ephem.Moon(),
    ephem.Mercury(),
    ephem.Venus(),
    ephem.Mars(),
    ephem.Jupiter(),
    ephem.Saturn()
    ]

planets_up = {}
for planet in planets:
    planets_up[planet.name] = None

observer = ephem.Observer()
observer.name = "Los Alamos"
observer.lon = '-106.2978'
observer.lat = '35.8911'
observer.elevation = 2286  # meters, though the docs don't actually say

# Loop from start date to end date,
# using a time of 10pm MST, which is 4am GMT the following day.
d = ephem.date('2014/7/19 04:00')
end_date = ephem.date('2017/1/1')
# For testing, this spans a Mars/Moon/Venus conjunction:
# d = ephem.date('2015/2/10 04:00')
# end_date = ephem.date('2015/3/10')

def datestr(d):
    tup = d.tuple()
    return "%d/%d/%d" % (tup[1], tup[2], tup[0])

def sepstr(sep):
    deg = float(sep) * 180. / math.pi
    # if deg < .5:
    #     return "less than a half a degree (%.2f)" % deg
    # if deg < 1.:
    #     return "less than a degree (%.2f)" % deg
    return "%.1f deg" % deg

print "Looking for planetary events between %s and %s" % (datestr(d),
                                                          datestr(end_date))

class ConjunctionPair:
    '''A conjunction between a pair of objects'''
    def __init__(self, b1, b2, date, sep):
        self.bodies = [b1, b2]
        self.date = date
        self.sep = sep

    def __repr__(self):
        return "%s: %s and %s, sep %s" % (datestr(self.date), self.bodies[0],
                                          self.bodies[1], sepstr(self.sep))

    def __contains__(self, body):
        return body in self.bodies

class Conjunction:
    '''A collection of ConjunctionPairs which may encompass more
       than two bodies and several days.
       The list is not guaranteed to be in date (or any other) order.
    '''
    def __init__(self):
        self.bodies = []
        self.pairs = []

    def __contains__(self, body):
        return body in self.bodies

    def add(self, body1, body2, date, sep):
        self.pairs.append(ConjunctionPair(body1, body2, date, sep))
        if body1 not in self.bodies:
            self.bodies.append(body1)
        if body2 not in self.bodies:
            self.bodies.append(body2)

    def start_date(self):
        date = ephem.date('3000/1/1')
        for pair in self.pairs:
            if pair.date < date:
                date = pair.date
        return date

    def end_date(self):
        date = ephem.date('0001/1/1')
        for pair in self.pairs:
            if pair.date > date:
                date = pair.date
        return date

    def find_min_seps(self):
        return mindate, maxdate, minseps

    def closeout(self):
        '''Time to figure out what we have and print it.'''

        # Find the list of minimum separations between each pair.
        startdate = ephem.date('3000/1/1')
        enddate = ephem.date('0001/1/1')
        minseps = []
        for i, b1 in enumerate(self.bodies):
            for b2 in self.bodies[i+1:]:
                minsep = 360  # degrees
                closest_date = None
                for pair in self.pairs:
                    if pair.date < startdate:
                        startdate = pair.date
                    if pair.date > enddate:
                        enddate = pair.date
                    if b1 in pair and b2 in pair:
                        if pair.sep < minsep:
                            minsep = pair.sep
                            closest_date = pair.date
                # Not all pairs will be represented. In a triple conjunction,
                # the two outer bodies may never get close enough to register
                # as a conjunction in their own right.
                if minsep < max_sep:
                    minseps.append((closest_date, minsep, b1, b2))
        minseps.sort()

        print "Conjunction of", ', '.join(self.bodies),
        print "lasts from %s to %s" % (datestr(startdate), datestr(enddate))
        for m in minseps:
            print "  %s and %s are closest on %s (%s)" % \
                (m[2], m[3], datestr(m[0]), sepstr(m[1]))

    def merge(self, conj):
        '''Merge in another Conjunction -- it must be that the two
           sets of pairs have bodies in common.
        '''
        for p in conj.pairs:
            self.pairs.append(p)
        for body in conj.bodies:
            if body not in self.bodies:
                self.bodies.append(body)

class ConjunctionList:
    '''A collection of Conjunctions -- no bodies should be shared
       between any of the conjunctions we contain.
    '''
    def __init__(self):
        self.clist = []

    def add(self, b1, b2, date, sep):
        for i, c in enumerate(self.clist):
            if b1 in c or b2 in c:
                c.add(b1, b2, date, sep)
                # But what if one of the bodies is already in one of our
                # other Conjunctions? In that case, we have to merge.
                for cc in self.clist[i+1:]:
                    if b1 in cc or b2 in cc:
                        c.merge(cc)
                        self.clist.delete(cc)
                return

        # It's new, so just add it
        c = Conjunction()
        c.add(b1, b2, date, sep)
        self.clist.append(c)

    def closeout(self):
        '''When we have a day with no conjunctions, check the list
           and close out any pending conjunctions.
        '''
        for c in self.clist:
            c.closeout()
        self.clist = []

oneday = ephem.hour * 24

def finish_planet(p, d):
    if planets_up[p]:
        print p, "visible from", \
            datestr(planets_up[p]),\
            "to", datestr(d)
        planets_up[planet.name] = None
    
conjunctions = ConjunctionList()
while d < end_date :
    #for planet in planets:
    #    planet.compute(observer)

    observer.date = d
    sunset = observer.previous_setting(sun)
    # sunrise = observer.next_rising(sun)
    # print  "Sunset:", sunset, "  Sunrise:", sunrise

    visible_planets = []
    for planet in planets:
        # A planet is observable this evening (not morning)
        # if its altitude at sunset OR its altitude at midnight
        # is greater than a threshold, which we'll set at 10 degrees.
        observer.date = sunset
        planet.compute(observer)
        # print planet.name, "alt at sunset:", planet.alt
        if planet.alt > min_alt:
            if not planets_up[planet.name]:
                # print datestr(d), planet.name, "is already up at sunset"
                planets_up[planet.name] = d;
            visible_planets.append(planet)

        else:
            # Try midnight
            midnight = list(observer.date.tuple())
            midnight[3:6] = [7, 0, 0]
            observer.date = ephem.date(tuple(midnight))
            if observer.date < sunset:
                observer.date += oneday
            planet.compute(observer)
            if planet.alt > min_alt:
                if not planets_up[planet.name]:
                    # print datestr(d), planet.name, "will rise before midnight"
                    planets_up[planet.name] = d;
                visible_planets.append(planet)
            else:
                # Planet is not up. Was it up yesterday?
                finish_planet(planet.name, d)

            # Go back to the sunset position, since that's the one
            # we'll use to compute separation.
            observer.date = sunset
            planet.compute(observer)

    # print datestr(d), "visible planets:", \
    #     ' '.join([p.name for p in visible_planets])
    # print "planets_up:", planets_up

    # Done with computing visible_planets.
    # Now look for conjunctions, anything closer than 5 degrees.
    saw_conjunction = False
    if len(visible_planets) > 1:
        for p, planet in enumerate(visible_planets):
            for planet2 in visible_planets[p+1:]:
                sep = ephem.separation(planet, planet2)
                if sep <= max_sep:
                    conjunctions.add(planet.name, planet2.name, d, sep)
                    saw_conjunction = True
    if not saw_conjunction:
        conjunctions.closeout()

    # Add a day:
    d = ephem.date(d + oneday)

for p in visible_planets:
    finish_planet(p.name, d)
