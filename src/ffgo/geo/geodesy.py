# geodesy.py --- Geodesic calculations
# -*- coding: utf-8 -*-
#
# Copyright (c) 2015  Florent Rougon
#
# This file is distributed under the terms of the DO WHAT THE FUCK YOU WANT TO
# PUBLIC LICENSE version 2, dated December 2004, by Sam Hocevar. You should
# have received a copy of this license along with this file. You can also find
# it at <http://www.wtfpl.net/>.

import sys
import itertools
import collections
import textwrap
import math
from math import degrees, radians, cos, sin, tan, atan, atan2, hypot, sqrt, \
    fmod

from ..constants import PROGNAME
from ..logging import logger
from ..exceptions import FFGoException

try:
    from geographiclib.geodesic import Geodesic
    HAS_GEOGRAPHICLIB = True
except ImportError:
    HAS_GEOGRAPHICLIB = False


class error(FFGoException):
    """Base class for exceptions in the geodesy module."""
    ExceptionShortDescription = _("Error caught in the geodesy module")

class VincentyInverseError(error):
    """
    Exception raised when the Vincenty-based method to solve the geodetic \
inverse problem fails."""
    ExceptionShortDescription = _("Unable to perform geodetic calculation")


def cosd(x):
    """Cosine of an angle given in degrees."""
    return cos(radians(x))

def sind(x):
    """Sine of an angle given in degrees."""
    return sin(radians(x))

def tand(x):
    """Tangent of an angle given in degrees."""
    return tan(radians(x))


def normAzimuth(azi):
    """Normalize an azimuth in degrees.

    Return a value x such as -180 <= x < 180 (this is the range
    GeographicLib seems to use when returning azimuths).

    """
    azi = fmod(azi, 360.0)      # result in the interval (-360, 360)

    if azi < -180.0:
        azi += 360.0

        if azi >= 180.0:        # -180.0 - 𝜀 + 360.0 can yield 180.0 if 𝜀
            azi = -180.0        # is small enough, but this value is not
                                # allowed here (𝜀 > 0)
    elif azi >= 180.0:
        azi -= 360.0

    return azi


def normLon(lon):
    """Normalize a longitude in degrees.

    Return a value x such as -180 <= x < 180 (not sure this is a general
    convention...).

    """
    return normAzimuth(lon)


def deltaLon(lon1, lon2):
    """Signed difference of two longitudes given in degrees.

    The input longitudes need not be normalized.
    Return a value x such as lon1 - lon2 = x + 360*n for some integer n
    and -180 <= x < 180.

    """
    # Take care of dangerous cases such as: lon1, lon2 = 0.0, -1e-320
    # In such a case, lon2 % 360.0 could be equal to 360.0 because of
    # the limited precision of floats. In order to avoid this, we start
    # by computing the difference, then use fmod(), because fmod(x, y)
    # is supposed to be exactly equal to x - n*y for some integer n, and
    # have the sign of x.
    d = fmod(lon1 - lon2, 360.0)
    if d >= 180.0:
        d -= 360.0
    elif d < -180.0:
        d += 360.0
        if d >= 180.0:    # -180.0 - 𝜀 + 360.0 can yield 180.0 if 𝜀 is small
            d = -180.0    # enough, but this value is not allowed here (𝜀 > 0)

    return d


def deltaLon2(lon1, lon2):
    """Signed difference of two longitudes given in degrees.

    The input longitudes need not be normalized.
    Return a value x such as lon1 - lon2 = x + 360*n for some integer n
    and -180 < x <= 180.

    """
    d = fmod(lon1 - lon2, 360.0)
    if d <= -180.0:
        d += 360.0
    elif d > 180.0:
        d -= 360.0
        if d <= -180.0:    # 180.0 + 𝜀 - 360.0 can yield -180.0 if 𝜀 is small
            d = 180.0      # enough, but this value is not allowed here (𝜀 > 0)

    return d


class NVector(collections.namedtuple('NVector', 'x y z')):
    """Simple class implementing n-vectors.

    cf. <https://en.wikipedia.org/wiki/N-vector>

    """
    __slots__  = ()             # no instance dictionary, save a bit of memory

    @classmethod
    def fromLatLon(cls, lat, lon):
        """n-vector for the point with given coordinates."""
        return cls(cosd(lat)*cosd(lon),
                   cosd(lat)*sind(lon),
                   sind(lat))

    def lat(self):
        """Latitude in degrees of the point represented by 'self'."""
        return degrees(atan2(self.z, hypot(self.x, self.y)))

    def lon(self):
        """Longitude in degrees of the point represented by 'self'."""
        return degrees(atan2(self.y, self.x))

    # “Inline” combination of lat() and lon() for convenience and performance
    def latLon(self):
        """
        Latitude and longitude in degrees of the point represented by 'self'."""
        return (degrees(atan2(self.z, hypot(self.x, self.y))),
                degrees(atan2(self.y, self.x)))

    def __add__(self, other):
        return NVector(self.x + other.x, self.y + other.y, self.z + other.z)

    def scalarMul(self, scalar):
        return NVector(scalar*self.x, scalar*self.y, scalar*self.z)

    def scalarDiv(self, scalar):
        return NVector(self.x / scalar, self.y / scalar, self.z / scalar)

    def dotProd(self, other):
        """Dot product of two vectors."""
        return self.x*other.x + self.y*other.y + self.z*other.z

    def crossProd(self, other):
        """Cross product of two vectors."""
        return NVector(self.y*other.z - self.z*other.y,
                       self.z*other.x - self.x*other.z,
                       self.x*other.y - self.y*other.x)

    def norm(self):
        """Euclidean norm of two vectors."""
        return sqrt(self.x*self.x + self.y*self.y + self.z*self.z)

    def angle(self, other):
        """Angle in radians between two vectors. Should be in [0, pi]."""
        # I believe this has better numerical behavior than the simpler
        # arccos-based formula.
        return atan2(self.crossProd(other).norm(), self.dotProd(other))


class EarthModel:
    """Constants from the WGS 84 model of the Earth."""

    a = 6378137.0               # length of semi-major axis of the ellipsoid
                                # (in meters)
    f = 1/298.257223563         # flattening of the ellipsoid
    b = (1-f)*a                 # length of semi-minor axis of the ellipsoid
    a2, b2 = a**2, b**2
    ab2 = a2*b2
    e2 = 1 - b2/a2              # squared eccentricity
    aSqrt1me2 = a*sqrt(1-e2)    # useful for the Gaussian radius of curvature

    @classmethod
    def meridionalRadius(cls, lat):
        """Return the meridional radius of curvature for a given latitude.

        The latitude should be given in degrees. This radius of
        curvature corresponds to the north-south direction and is often
        referred to as 'M'.

        """
        return cls.ab2 / ((cls.a*cosd(lat))**2 + (cls.b*sind(lat))**2)**1.5

    @classmethod
    def normalRadius(cls, lat):
        """Return the normal radius of curvature for a given latitude.

        The latitude should be given in degrees. This radius of
        curvature corresponds to the east-west direction and is often
        referred to as 'N'.

        """
        return cls.a2 / sqrt((cls.a*cosd(lat))**2 + (cls.b*sind(lat))**2)

    @classmethod
    def gaussRadius(cls, lat):
        """Return the Gaussian radius of curvature for a given latitude.

        The latitude should be given in degrees.

        """
        sinPhi = sind(lat)
        return cls.aSqrt1me2 / (1-cls.e2*sinPhi*sinPhi)


class GeodCalc:
    """Class for performing basic geodesic calculations."""

    def __init__(self):
        self.earthModel = EarthModel()

    @classmethod
    def greatCircleAzimuths(cls, lat1, lon1, lat2, lon2):
        """Return start and stop azimuths on a great circle, in degrees.

        This of course uses a real sphere, not an ellipsoid.

        """
        if lat1 == lat2 and not deltaLon(lon1, lon2):
            raise ValueError("cannot compute azimuths for null arc")
        elif lat1 in (-90.0, 90.0) or lat2 in (-90.0, 90.0):
            if lat1 == lat2:
                raise ValueError("cannot compute azimuths for null arc")
            elif lat1 == 90 or lat2 == -90:
                return (180.0, 180.0)
            elif lat1 == -90 or lat2 == 90:
                return (0.0, 0.0)
            else:
                assert False, \
                    "should not get there: lat1 = {!r} and lat2 = {!r}".format(
                        lat1, lat2)

        l12 = radians(lon2-lon1)
        a1 = atan2(sin(l12),
                   cosd(lat1)*tand(lat2) - sind(lat1)*cos(l12))
        a2 = atan2(sin(l12),
                   -cosd(lat2)*tand(lat1) + sind(lat2)*cos(l12))

        return tuple(map(lambda x: normAzimuth(degrees(x)),
                         (a1, a2)))

    def vincentyInverse(self, lat1, lon1, lat2, lon2, precision=1e-12):
        """Vincenty's algorithm for the geodetic inverse problem.

        The latitudes and longitudes must be given in degrees. The
        return value is a dictionary 'd' such as:
          - d["s12"] is the length in meters of the shortest path
            between the two specified points;
          - d["azi1"] is the azimuth in degrees at point 1 on the path;
          - d["azi2"] is the (forward) azimuth in degrees at point 2 on
            the path.

        This return value is a sort of "subset" of the return value of
        GeographicLib's Geodesic.WGS84.Inverse(). The returned azimuths
        are normalized with normAzimuth().

        """
        f = self.earthModel.f               # for fast access (used in the loop)
        b = self.earthModel.b               # only for readability
        a2 = self.earthModel.a2
        b2 = self.earthModel.b2

        U1 = atan((1-f)*tan(radians(lat1))) # reduced latitude
        U2 = atan((1-f)*tan(radians(lat2))) # ditto
        cosU1, sinU1 = cos(U1), sin(U1)     # precompute all these quantities
        cosU2, sinU2 = cos(U2), sin(U2)
        cosU1cosU2 = cosU1*cosU2
        cosU1sinU2 = cosU1*sinU2
        sinU1cosU2 = sinU1*cosU2
        sinU1sinU2 = sinU1*sinU2
        lb = L = radians(lon2-lon1)

        maxIterations = 500
        for count in itertools.count():
            if count and (abs(lb - prevLb) < precision or
                          count == maxIterations):
                break
            prevLb = lb

            sinSigma = hypot(cosU2*sin(lb), cosU1sinU2 - sinU1cosU2*cos(lb))
            cosSigma = sinU1sinU2 + cosU1cosU2*cos(lb)
            sigma = atan2(sinSigma, cosSigma)
            sinAlpha = cosU1cosU2*sin(lb) / sinSigma
            sqCosAlpha = 1 - sinAlpha**2
            cos2sigmaM = cosSigma - 2*sinU1sinU2/sqCosAlpha
            C = f/16 * sqCosAlpha*(4 + f*(4 - 3*sqCosAlpha))
            lb = L + (1-C)*f*sinAlpha*(
                sigma + C*sinSigma*(cos2sigmaM +
                                    C*cosSigma*(-1+2*cos2sigmaM**2)))

        if count == maxIterations:
            raise VincentyInverseError(
                "the Vincenty algorithm doesn't seem to converge")

        u2 = sqCosAlpha*(a2 - b2)/b2
        A = 1 + u2/16384 * (4096 + u2*(-768 + u2*(320 - 175*u2)))
        B = u2/1024 * (256 + u2*(-128 + u2*(74 - 47*u2)))
        deltaSigma = B*sinSigma*(
            cos2sigmaM + 0.25*B*(
                cosSigma*(-1+2*cos2sigmaM**2) -
                B/6*cos2sigmaM*(-3+4*sinSigma**2)*(-3+4*cos2sigmaM**2)))
        s = b*A*(sigma - deltaSigma)
        azi1 = degrees(atan2(cosU2*sin(lb), cosU1sinU2 - sinU1cosU2*cos(lb)))
        azi2 = degrees(atan2(cosU1*sin(lb), -sinU1cosU2 + cosU1sinU2*cos(lb)))

        return {"s12": s,
                "azi1": normAzimuth(azi1),
                "azi2": normAzimuth(azi2)}

    # If this method is renamed, 'fName' below must be changed too.
    def vincentyInverseWithFallback(self, lat1, lon1, lat2, lon2,
                                    precision=1e-12):
        """Vincenty's algorithm for the geodetic inverse problem + fallbacks.

        Use Vincenty's algorithm to solve the geodetic inverse problem,
        plus additional methods for cases where it doesn't work. The
        main cases these fallbacks are used for are:
          - start and end points identical or very close to each other;
          - equatorial lines between points that are not antipodal nor
            nearly so.

        In the case of antipodal or nearly antipodal end points,
        VincentyInverseError is raised. Because of the Earth's flatness,
        finding the correct azimuths in such cases is very difficult
        (spherical approximation can't be used). This is solved by
        Karney's algorithm implemented in GeographicLib, but not here.

        Note: the 'precision' optional argument is only used with
              Vincenty's algorithm.

        """
        fName = "vincentyInverseWithFallback"
        textWidth = 78          # for wrapping of log messages

        if (lat1 == lat2 == 90.0 or lat1 == lat2 == -90.0 or
            lat1 == lat2 and normLon(lon1) == normLon(lon2)):
            logger.debugNP("{f}: identical start and end points, "
                           "short-circuiting the whole process".format(
                               f=fName))
            # Make sure the distance returned in this case is exactly zero.
            return {"s12": 0.0, "azi1": 0.0, "azi2": 0.0}

        try:
            res = self.vincentyInverse(lat1, lon1, lat2, lon2,
                                       precision=precision)
            logger.debugNP("{f}: Vincenty method worked".format(
                f=fName))
            return res
        except (ZeroDivisionError, VincentyInverseError) as exc:
            n1 = NVector.fromLatLon(lat1, lon1)
            n2 = NVector.fromLatLon(lat2, lon2)
            angle = n1.angle(n2)    # radians

            # 'angle' should be non-negative unless the atan2() implementation
            # used in NVector.angle() manages to change the sign of the result
            # because of floating point inaccuracy...
            if abs(angle) < 400/6371: # 400 km
                if (lat1 > 80 and lat2 > 80 or lat1 < -80 and lat2 < -80):
                    # Not accurate here, but the end result shouldn't be worse
                    # than if using fccDistance().
                    phi_m = 0.5*(lat1 + lat2)
                    dist = self.earthModel.gaussRadius(phi_m)*angle
                    logger.debugNP(textwrap.fill(textwrap.dedent("""\
                      {f}: Vincenty method didn't work; points not very far
                      away from each other and close to one of the poles
                      (angle = {ang!r}°, lat1 = {lat1!r}, lat2 = {lat2!r}),
                      dist = {d!r} m obtained using the Gaussian radius of
                      curvature""").format(f=fName, ang=degrees(angle),
                                           lat1=lat1, lat2=lat2, d=dist),
                                                 width=textWidth))
                else:
                    dist = self.fccDistance(lat1, lon1, lat2, lon2)
                    logger.debugNP(textwrap.fill(textwrap.dedent("""\
                      {f}: Vincenty method didn't work; points not very far
                      away from each other (angle = {ang!r}°), dist = {d!r} m
                      obtained with fccDistance()""").format(
                            f=fName, ang=degrees(angle), d=dist),
                                                 width=textWidth))

                try:
                    azi1, azi2 = self.greatCircleAzimuths(
                        lat1, lon1, lat2, lon2)
                except ValueError:
                    assert dist < 1e-6, dist # should be zero, actually
                    logger.debugNP(textwrap.fill(textwrap.dedent("""\
                      {f}: could not compute azimuths; barring rounding errors,
                      the points should be equal""").format(f=fName, d=dist),
                                                 width=textWidth))
                    return {"s12": 0.0, "azi1": 0.0, "azi2": 0.0}
                else:
                    logger.debugNP("{f}: using spherical approximation to "
                                   "compute the azimuths".format(f=fName))
                    return {"s12": dist, "azi1": azi1, "azi2": azi2}
            # As above, math.pi - angle should already be non-negative. Use
            # abs() just in case.
            elif abs(math.pi - angle) < 0.1: # nearly antipodal points
                logger.debugNP("{f}: nearly antipodal points "
                               "(angle = {ang!r}°)"
                               .format(f=fName, ang=degrees(angle)))
                # Because of the Earth's flatness, the shortest path is not
                # easy to guess. It should pass close to one of the poles;
                # spherical approximation would give completely wrong
                # azimuths!
                self._vincentyRaiseExcForAntipodalPoints(exc)
            else:
                # The following fallback method is particularly useful for
                # equatorial lines whose central angle is not too close to 180°
                # (i.e., the endpoints are neither antipodal nor nearly so).
                try:
                    # Spherical approximation
                    azi1, azi2 = self.greatCircleAzimuths(
                        lat1, lon1, lat2, lon2)
                except ValueError:
                    assert False, "should not get there"
                else:
                    logger.debugNP(textwrap.fill(textwrap.dedent("""\
                      {f}: using spherical approximation to compute the
                      azimuths, and Gaussian radius of curvature to
                      estimate the distance based on the central angle
                      (angle = {ang!r}°)""")
                        .format(f=fName, ang=degrees(angle)),
                                                 width=textWidth))
                    # This “mean latitude” would be a pretty bad guess
                    # if the start and end points were located on either
                    # side of a pole, but this code path should not be
                    # reachable in such a case.
                    phi_m = 0.5*(lat1 + lat2)
                    dist = self.earthModel.gaussRadius(phi_m)*angle
                    return {"s12": dist, "azi1": azi1, "azi2": azi2}

    def _vincentyRaiseExcForAntipodalPoints(self, origExc):
        msg = (textwrap.fill(textwrap.dedent(_("""\
          your latest interactions with {prg} required to perform a geodetic
          calculation. {prg} tried to do it with Vincenty's “formula” (rather,
          algorithm) and a few others, but this is not possible because the two
          points are antipodal or nearly so, which is the main difficult case
          where this algorithm is known not to work. Easier cases can be worked
          around using a spherical approximation of the Earth, but in this
          precise case, that would give completely wrong azimuths, and I prefer
          stopping like this rather than giving you an erroneous result.""")),
                             width=sys.maxsize)
               + "\n\n" +
               textwrap.fill(textwrap.dedent(_("""\
          {prg} can do the same calculation with GeographicLib, a library
          containing fairly recent, sophisticated algorithms by Charles
          F. F. Karney, that are supposed to handle all cases of the geodetic
          inverse problem. If you want {prg} to do that, you have to install
          GeographicLib for the Python interpreter used to run {prg}. You just
          have to restart {prg} after the installation; GeographicLib will be
          automatically found and used for such calculations.""")),
                             width=sys.maxsize)).format(prg=PROGNAME)

        raise VincentyInverseError(msg) from origExc

    def karneyInverse(self, lat1, lon1, lat2, lon2):
        """Use Karney's algorithm for the geodetic inverse problem."""
        return Geodesic.WGS84.Inverse(lat1, lon1, lat2, lon2)

    @classmethod
    def karneyMethodAvailable(cls):
        return HAS_GEOGRAPHICLIB

    def inverse(self, lat1, lon1, lat2, lon2, precision=1e-12):
        """Solve the geodetic inverse problem.

        Use Karney's algorithm if available, otherwise Vincenty's method
        with a few simpler fallbacks when it doesn't work (except for
        the difficult case of antipodal or nearly antipodal end points,
        which is only handled by Karney's algorithm).

        See vincentyInverse() for information on the return value.

        Note: the 'precision' optional argument is only used with
              Vincenty's algorithm.

        """
        if HAS_GEOGRAPHICLIB:
            return self.karneyInverse(lat1, lon1, lat2, lon2)
        else:
            return self.vincentyInverseWithFallback(lat1, lon1, lat2, lon2,
                                                    precision=precision)

    def _fccK1(self, phi_m):
        """Approx. number of kilometers per degree of latitude.

        K1 = M*pi/180 where M is the meridional radius of curvature at
        latitude 'phi_m' (based on an ellipsoidal model of the Earth.
        'phi_m' must be given in radians.

        """
        return 111.13209 - 0.56605*cos(2*phi_m) + 0.00120*cos(4*phi_m)

    def _fccK2(self, phi_m):
        """Approx. number of kilometers per degree of longitude.

        K2 = cos(phi_m)*N*pi/180 where N is the radius of curvature in
        the prime vertical at latitude phi_m (based on an ellipsoidal
        model of the Earth. 'phi_m' must be given in radians.

        """
        return (111.41513*cos(phi_m) - 0.09455*cos(3*phi_m) +
                0.00012*cos(5*phi_m))

    def fccDistance(self, lat1, lon1, lat2, lon2):
        """
        Approx. distance based on ellipsoidal Earth model projected to a plane.

        cf. <https://en.wikipedia.org/wiki/Geographical_distance>.
        lat1, lon1, lat2, lon2: geodetic coordinates in degrees

        This method is supposed to give acceptable results for distances
        not exceeding 475 km / 295 miles, when not too close to the
        North or South pole. Return the distance in meters.

        """
        phi_m = radians(0.5*(lat1 + lat2))

        # Convert from kilometers to meters
        return 1000*hypot(self._fccK1(phi_m)*(lat2 - lat1),
                          self._fccK2(phi_m)*deltaLon(lon2, lon1))

    def modifiedFccDistance(self, lat1, lon1, lat2, lon2):
        """
        Approx. distance based on ellipsoidal Earth model projected to a plane.

        This is the same as fccDistance(), except that spherical
        approximation using the Gaussian radius of curvature will be
        used if both points are not too far away from one of the poles.
        fccDistance() would “unroll” a circle of constant latitude
        instead of “cutting” through the closest pole, which would be
        pretty far from the shortest path (especially if the longitudes
        differ by 180° or something not too far).

        """
        # Actually, the problem with fccDistance() addressed here can
        # happen at any latitude provided the longitudes differ by 180°
        # or so (the shortest path passes close to a pole, and the large
        # difference between the longitudes doesn't by itself contribute
        # to the length of the path). But if this is the case and the
        # points are not close to one of the poles, then they must be
        # quite distant and this method shouldn't be used in the first
        # place.
        if (lat1 > 80 and lat2 > 80 or lat1 < -80 and lat2 < -80):
            n1 = NVector.fromLatLon(lat1, lon1)
            n2 = NVector.fromLatLon(lat2, lon2)
            angle = n1.angle(n2)    # radians

            # Not accurate here, but the end result shouldn't be worse
            # than if using fccDistance().
            lat_m = 0.5*(lat1 + lat2)
            dist = self.earthModel.gaussRadius(lat_m)*angle
        else:
            dist = self.fccDistance(lat1, lon1, lat2, lon2)

        return dist
