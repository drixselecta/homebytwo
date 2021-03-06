from django.contrib.auth.models import User
from django.contrib.gis.db import models

from social_django.models import UserSocialAuth
from social_django.utils import load_strategy
from stravalib.client import Client as StravaClient

from homebytwo.importers.exceptions import StravaMissingCredentials


class Athlete(models.Model):
    # Extend default user model
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    # has the initial import of all Strava activities already taken place?
    activities_imported = models.BooleanField(default=False)

    def __str__(self):
        return str(self.user.username)

    @property
    def strava_client(self):
        """
        the Strava API client instantiated with the athlete's
        authorization token. Note that it only generates a hit to the Strava
        API if the authorization token is expired.
        """

        # retrieve the access token from the user with social auth
        try:
            social = self.user.social_auth.get(provider="strava")

        except UserSocialAuth.DoesNotExist:
            raise StravaMissingCredentials

        strava_access_token = social.get_access_token(load_strategy())

        # return the Strava client
        return StravaClient(access_token=strava_access_token)

    @property
    def strava_id(self):
        return self.user.social_auth.get(provider="strava").uid


"""
A snippet to create an athlete profile the first time it is accessed.
https://www.djangorocks.com/snippets/automatically-create-a-django-profile.html
"""
User.athlete = property(lambda u: Athlete.objects.get_or_create(user=u)[0])
