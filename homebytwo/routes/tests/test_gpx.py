import json
from os.path import dirname, realpath
from xml.dom import minidom

from django.conf import settings
from django.contrib.gis.geos import Point
from django.test import TestCase, override_settings
from django.urls import reverse

import httpretty
from garmin_uploader import api as garmin_api
from mock import patch

from ...utils.factories import AthleteFactory
from ..tasks import upload_route_to_garmin_task
from ..utils import GARMIN_ACTIVITY_TYPE_MAP
from .factories import PlaceFactory, RouteFactory

CURRENT_DIR = dirname(realpath(__file__))


@override_settings(
    GARMIN_CONNECT_USERNAME="example@example.com",
    GARMIN_CONNECT_PASSWORD="testpassword",
    GARMIN_ACTIVITY_URL="https://example.com/garmin/{}",
)
class GPXTestCase(TestCase):
    def setUp(self):
        self.athlete = AthleteFactory(user__password="testpassword")
        self.client.login(username=self.athlete.user.username, password="testpassword")
        self.route = RouteFactory(athlete=self.athlete)

        # add checkpoints to the route
        number_of_checkpoints = 9
        for index in range(1, number_of_checkpoints + 1):
            line_location = index / (number_of_checkpoints + 1)
            place = PlaceFactory(
                geom=Point(
                    *self.route.geom.coords[
                        int(self.route.geom.num_coords * line_location)
                    ]
                )
            )
            self.route.places.add(
                place, through_defaults={"line_location": line_location}
            )

    def test_gpx_no_start_no_end_no_checkpoints(self):
        self.route.calculate_projected_time_schedule(self.athlete.user)
        self.route.checkpoint_set.all().delete()
        self.route.start_place = None
        self.route.end_place = None

        xml_doc = minidom.parseString(self.route.get_gpx())
        waypoints = xml_doc.getElementsByTagName("wpt")
        track = xml_doc.getElementsByTagName("trk")

        self.assertEqual(len(waypoints), 0)
        self.assertEqual(len(track), 1)

    def test_gpx_success(self):
        self.route.calculate_projected_time_schedule(self.athlete.user)
        xml_doc = minidom.parseString(self.route.get_gpx())
        waypoints = xml_doc.getElementsByTagName("wpt")
        trackpoints = xml_doc.getElementsByTagName("trkpt")

        self.assertEqual(len(waypoints), self.route.places.count() + 2)
        self.assertEqual(len(trackpoints), len(self.route.data.index))

    def test_download_route_gpx_view(self):
        wpt_xml = '<wpt lat="{1}" lon="{0}">'
        xml_start_place = wpt_xml.format(*self.route.start_place.get_coords())
        xml_end_place = wpt_xml.format(*self.route.end_place.get_coords())
        xml_waypoints = [
            wpt_xml.format(*place.get_coords()) for place in self.route.places.all()
        ]
        xml_segment_name = "<name>{}</name>".format(self.route.name)

        url = reverse("routes:gpx", kwargs={"pk": self.route.pk})
        response = self.client.get(url)
        file_content = b"".join(response.streaming_content).decode("utf-8")

        for xml_waypoint in xml_waypoints:
            self.assertIn(xml_waypoint, file_content)

        self.assertIn(xml_start_place, file_content)
        self.assertIn(xml_end_place, file_content)
        self.assertIn(xml_segment_name, file_content)

    def test_download_route_gpx_other_athlete_view(self):
        second_athlete = AthleteFactory(user__password="123456")
        self.client.login(username=second_athlete.user.username, password="123456")

        gpx_url = reverse("routes:gpx", kwargs={"pk": self.route.pk})
        response = self.client.get(gpx_url)

        self.assertEqual(response.status_code, 404)

    def test_download_route_gpx_route_with_no_schedule(self):
        assert "schedule" not in self.route.data.columns

        response = self.client.get(reverse("routes:gpx", kwargs={"pk": self.route.pk}))
        file_content = b"".join(response.streaming_content).decode("utf-8")

        self.assertIn("<name>{}</name>".format(self.route.name), file_content)

    @override_settings(GARMIN_ACTIVITY_URL="https://example.com/garmin/{}")
    def test_garmin_activity_url(self):
        self.route.garmin_id = 123456
        self.route.save(update_fields=["garmin_id"])
        garmin_url = settings.GARMIN_ACTIVITY_URL.format(self.route.garmin_id)

        response = self.client.get(
            reverse("routes:route", kwargs={"pk": self.route.id})
        )
        self.assertContains(response, garmin_url)

    def test_garmin_upload_not_route_athlete(self):
        second_athlete = AthleteFactory(user__password="123456")
        self.client.login(username=second_athlete.user.username, password="123456")
        response = self.client.get(
            reverse("routes:garmin_upload", args=[self.route.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_garmin_upload_view_success(self):
        upload_url = reverse("routes:garmin_upload", args=[self.route.pk])
        route_url = reverse("routes:route", args=[self.route.pk])

        with patch(
            "homebytwo.routes.tasks.upload_route_to_garmin_task.delay"
        ) as mock_task:
            response = self.client.get(upload_url)
            self.assertRedirects(response, route_url)
            self.assertTrue(mock_task.called)

    def block_garmin_authentication_urls(self):
        """
        helper task to authenticate with the Garmin uploader blocking all calls
        """

        # get hostname
        host_name_response = '{"host": "https://connect.garmin.com"}'
        httpretty.register_uri(
            httpretty.GET,
            garmin_api.URL_HOSTNAME,
            body=host_name_response,
            content_type="application/json",
        )

        # get login form
        get_login_body = '<input type="hidden" name="_csrf" value="CSRF" />'
        httpretty.register_uri(
            httpretty.GET,
            garmin_api.URL_LOGIN,
            body=get_login_body,
            match_querystring=False,
        )

        # sign-in
        sign_in_body = "var response_url = 'foo?ticket=bar'"
        httpretty.register_uri(
            httpretty.POST,
            garmin_api.URL_LOGIN,
            body=sign_in_body,
            match_querystring=False,
            adding_headers={
                "set-cookie": "GARMIN-SSO-GUID=foo; Domain=garmin.com; Path=/"
            },
        )

        # redirect to some place
        post_login = "almost there..."
        httpretty.register_uri(
            httpretty.GET,
            garmin_api.URL_POST_LOGIN,
            body=post_login,
            match_querystring=False,
        )

        # check login
        check_login = '{"fullName": "homebytwo"}'
        httpretty.register_uri(
            httpretty.GET,
            garmin_api.URL_PROFILE,
            body=check_login,
            content_type="application/json",
        )

    def block_garmin_upload_urls(self, garmin_activity_id):

        activity_url = "{}/{}".format(garmin_api.URL_ACTIVITY_BASE, garmin_activity_id)

        # upload activity
        upload_url = "{}/{}".format(garmin_api.URL_UPLOAD, ".gpx")
        upload_activity_response = {
            "detailedImportResult": {"successes": [{"internalId": garmin_activity_id}]}
        }
        httpretty.register_uri(
            httpretty.POST,
            upload_url,
            body=json.dumps(upload_activity_response),
            content_type="application/json",
        )

        # update activity
        httpretty.register_uri(
            httpretty.POST, activity_url, body="yeah!",
        )

        # get activity types
        activity_type = GARMIN_ACTIVITY_TYPE_MAP.get(
            self.route.activity_type.name, "other"
        )
        activity_type_response = [{"typeKey": activity_type}]
        httpretty.register_uri(
            httpretty.GET,
            garmin_api.URL_ACTIVITY_TYPES,
            body=json.dumps(activity_type_response),
            content_type="application/json",
        )

    def block_garmin_delete_urls(self, garmin_activity_id, status=200):
        # delete activity
        delete_url = "https://connect.garmin.com/modern/proxy/activity-service/activity/{}".format(
            garmin_activity_id
        )
        httpretty.register_uri(
            httpretty.DELETE, delete_url, body="",
            status=status,
        )

    def blocked_garmin_upload_task(self, route=None, athlete=None):
        """
        helper method to upload a route to Garmin while blocking all external calls
        """
        route = route or self.route
        athlete = athlete or self.athlete
        garmin_activity_id = self.route.garmin_id or 654321

        httpretty.enable()

        self.block_garmin_authentication_urls()
        self.block_garmin_upload_urls(garmin_activity_id)
        self.block_garmin_delete_urls(garmin_activity_id)

        response = upload_route_to_garmin_task(route.pk, athlete.id)

        httpretty.disable()

        return response

    def test_garmin_upload_task_success(self):
        self.route.garmin_id = 123456
        self.route.save(update_fields=["garmin_id"])

        message = "Route '{route}' successfully uploaded to Garmin connect at {url}"
        route_str = str(self.route)

        response = self.blocked_garmin_upload_task()

        self.route.refresh_from_db()
        garmin_activity_url = self.route.garmin_activity_url

        self.assertIn(
            response, message.format(route=route_str, url=garmin_activity_url)
        )

    def test_garmin_upload_task_old_route_success(self):

        assert "schedule" not in self.route.data.columns
        self.route.garmin_id = 1

        self.route.save(update_fields=["data", "garmin_id"])

        message = "Route '{route}' successfully uploaded to Garmin connect at {url}"
        route_str = str(self.route)

        response = self.blocked_garmin_upload_task()

        self.route.refresh_from_db()
        garmin_activity_url = self.route.garmin_activity_url

        self.assertIn(
            response, message.format(route=route_str, url=garmin_activity_url)
        )
        self.assertIn("schedule", self.route.data.columns)

    def test_garmin_upload_other_athlete(self):
        self.route.garmin_id = 1
        self.route.save(update_fields=["garmin_id"])

        second_athlete = AthleteFactory(user__password="123456")
        self.client.login(username=second_athlete.user.username, password="123456")

        message = "Route '{route}' successfully uploaded to Garmin connect at {url}"
        route_str = str(self.route)

        response = self.blocked_garmin_upload_task(athlete=second_athlete)

        self.route.refresh_from_db()
        garmin_activity_url = self.route.garmin_activity_url

        self.assertIn(
            response, message.format(route=route_str, url=garmin_activity_url)
        )

    def test_garmin_upload_failure_cannot_signin(self):
        self.route.garmin_id = 1
        self.route.save(update_fields=["garmin_id"])

        httpretty.enable(allow_net_connect=False)

        # fail auth quickly
        httpretty.register_uri(
            httpretty.GET,
            garmin_api.URL_HOSTNAME,
            body="{}",
            content_type="application/json",
            status=500,
        )

        response = upload_route_to_garmin_task(self.route.pk, self.athlete.id)
        httpretty.disable()

        self.assertIn("Garmin API failure:", response)

    def test_garmin_delete_failure(self):
        self.route.garmin_id = 123456
        self.route.save(update_fields=["garmin_id"])

        httpretty.enable(allow_net_connect=False)

        self.block_garmin_authentication_urls()
        self.block_garmin_delete_urls(self.route.garmin_id, status=500)

        response = upload_route_to_garmin_task(self.route.pk, self.athlete.id)

        httpretty.disable()

        self.assertIn("Failed to delete activity", response)
