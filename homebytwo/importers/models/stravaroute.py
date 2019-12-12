from django.contrib.gis.geos import LineString

from pandas import DataFrame
from social_django.models import UserSocialAuth
from stravalib import unithelper

from ...routes.models import ActivityType, Route, RouteManager
from ...routes.utils import Link
from ..exceptions import StravaMissingCredentials


class StravaRouteManager(RouteManager):
    def get_queryset(self):
        """
        Returns querysets with Strava Routes only.
        This method is required because StravaRoute
        is a proxy class.
        Methods from the RouteManager, e.g. for_user can also be used.
        """
        return super().get_queryset().filter(data_source="strava")

    # login to Strava and retrieve route list
    def get_remote_routes_list(self, athlete, session):
        """
        fetches the athlete's routes list from Strava and returns them
        as a list of StravaRoute stubs.
        """

        # retrieve routes list from Strava
        strava_routes = athlete.strava_client.get_routes(athlete_id=athlete.strava_id)

        # create model instances with Strava routes data
        return [
            StravaRoute(
                source_id=strava_route.id,
                name=strava_route.name,
                totalup=unithelper.meters(strava_route.elevation_gain).num,
                length=unithelper.meters(strava_route.distance).num,
                athlete=athlete,
            )
            for strava_route in strava_routes
        ]

    def check_user_credentials(self, request):
        """
        view function provided to check whether a user
        has access to Strava.
        """
        # check if the user has an associated Strava account
        try:
            request.user.social_auth.get(provider="strava")

        # redirect to login with strava page
        except UserSocialAuth.DoesNotExist:
            raise StravaMissingCredentials


class StravaRoute(Route):

    """
    Proxy for Route Model with specific methods and custom manager.
    """

    # data source name to display in templates
    DATA_SOURCE_NAME = "Strava"
    DATA_SOURCE_LINK = Link("https://www.strava.com/athlete/routes", DATA_SOURCE_NAME,)

    def __init__(self, *args, **kwargs):
        """
        Set the data_source of the route to strava
        when instatiatind a route.
        """
        super().__init__(*args, **kwargs)
        self.data_source = "strava"

    class Meta:
        proxy = True

    # custom manager
    objects = StravaRouteManager()

    # retrieve strava information for a route
    def get_route_details(self):
        """
        retrieve route details including streams from strava.
        the source_id of the model instance must be set.
        """

        # Retrieve route details from Strava API
        strava_client = self.athlete.strava_client
        strava_route = strava_client.get_route(self.source_id)

        # set route name
        self.name = strava_route.name

        # Strava only knows two activity types for routes: '1' for ride, '2' for run
        if strava_route.type == "1":
            self.activity_type = ActivityType.objects.get(name=ActivityType.RIDE)
        if strava_route.type == "2":
            self.activity_type = ActivityType.objects.get(name=ActivityType.RUN)

        # create route data from Strava API streams
        self.data = self.get_route_data_streams(strava_client)

        # save route geom from latlng stream and drop redundant column in data
        self.geom = LineString(*self.data["latlng"], srid=4326)
        self.data.drop(columns=["latlng"], inplace=True)

    def get_route_data_streams(self, strava_client):
        """
        convert route raw streams into a pandas DataFrame.
        the stravalib client creates a list of dicts:
        `[stream_type: <Stream object>, stream_type: <Stream object>, ...]`
        """
        # retrieve route streams from Strava API
        route_streams = strava_client.get_route_streams(self.source_id)

        data = DataFrame()

        for key, stream in route_streams.items():
            # rename distance to length
            if key == "distance":
                data["length"] = stream.data
            else:
                data[key] = stream.data

        return data
