from json import dumps as json_dumps

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.gis.geos import LineString, Point

import gpxpy
from pandas import DataFrame
from requests import Session, codes

from homebytwo.routes.models import Route
from homebytwo.routes.utils import get_distances


class SwitzerlandMobilityLogin(forms.Form):
    """
    This form prompts the user for his Switzerland Mobility Login
    and retrieves a session cookie.
    Credentials are not stored in the Database.
    """

    username = forms.CharField(
        label="Username",
        max_length=100,
        widget=forms.EmailInput(
            attrs={"placeholder": "Username on Switzerland Mobility Plus"}
        ),
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={"placeholder": "Password on Switzerland Mobility Plus"}
        ),
    )

    def retrieve_authorization_cookie(self, request):
        """
        Retrieves auth cookies from Switzerland Mobility
        and returns cookies or False
        The cookies are required to display a user's list of saved routes.

        Example response from the Switzerland Mobility login URL:
        {
          'loginErrorMsg': '',
          'userdata': {
            ...
          },
          'loginErrorCode': 200,
          'loginconfig': {
            ...
          }
        }

        Cookies returned by login URL in case of successful login:
        {'srv': 'xxx', 'mf-chmobil': 'xxx'}
        """

        login_url = settings.SWITZERLAND_MOBILITY_LOGIN_URL

        credentials = {
            "username": self.cleaned_data["username"],
            "password": self.cleaned_data["password"],
        }

        with Session() as session:

            # Try to login to map.wanderland.ch
            login_request = session.post(login_url, data=json_dumps(credentials))

            if login_request.status_code == codes.ok:

                # log-in was successful, return cookies
                if login_request.json()["loginErrorCode"] == 200:
                    cookies = dict(login_request.cookies)
                    message = "Successfully logged-in to Switzerland Mobility"
                    messages.success(request, message)
                    return cookies

                # log-in failed
                else:
                    message = login_request.json()["loginErrorMsg"]
                    messages.error(request, message)
                    return False

            # Some other server error
            else:
                message = (
                    "Error %s: logging to Switzerland Mobility. "
                    "Try again later" % login_request.status_code
                )
                messages.error(request, message)
                return False


class GpxUploadForm(forms.Form):
    gpx = forms.FileField()

    def clean_gpx(self):
        gpx_file = self.cleaned_data["gpx"]
        try:
            return gpxpy.parse(gpx_file)
        except gpxpy.gpx.GPXXMLSyntaxException as e:
            raise forms.ValidationError(
                f'Your file doesn\'t appear to be a valid GPX file (error was: "{str(e)}")'
            )

    def save(self, commit=True):
        gpx = self.cleaned_data["gpx"]
        points = gpx.tracks[0].segments[0].points

        route = Route(source_id=None)
        (
            route.total_elevation_gain,
            route.total_elevation_loss,
        ) = gpx.get_uphill_downhill()
        # FIXME use length_3d once `Route.geom` has been converted to 3d
        route.total_distance = gpx.length_2d()
        # FIXME include `point.elevation` in the tuple once `Route.geom` has been converted to 3d
        coords = [(point.longitude, point.latitude) for point in points]
        route.geom = LineString(coords, srid=4326).transform(21781, clone=True)

        distances = get_distances([Point(p) for p in route.geom])
        route_data = [
            {"distance": distance, "altitude": point.elevation,}
            for point, distance in zip(points, distances)
        ]
        route.data = DataFrame(route_data, columns=["distance", "altitude"])

        if commit:
            route.save()

        return route
