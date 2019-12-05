import json
from copy import deepcopy
from datetime import timedelta
from os.path import dirname, realpath

from django.test import TestCase, override_settings
from django.urls import reverse

import httpretty
from mock import patch

from ...utils.factories import AthleteFactory, UserFactory
from ...utils.tests import read_data
from ..models import Activity, Gear, WebhookTransaction
from ..tasks import ProcessStravaEvents
from .factories import ActivityFactory, GearFactory, WebhookTransactionFactory

CURRENT_DIR = dirname(realpath(__file__))


class ActivityTestCase(TestCase):

    STRAVA_BASE_URL = "https://www.strava.com/api/v3"
    PROCESSED = WebhookTransaction.PROCESSED
    UNPROCESSED = WebhookTransaction.UNPROCESSED
    SKIPPED = WebhookTransaction.SKIPPED
    ERROR = WebhookTransaction.ERROR

    def setUp(self):
        self.athlete = AthleteFactory(user__password="testpassword")
        self.client.login(username=self.athlete.user.username, password="testpassword")

    def load_strava_activity_from_json(self, file):
        """
        helper to turn Strava API json results into stravalib client objects
        """
        strava_activity_json = read_data(file, dir_path=CURRENT_DIR)
        strava_activity_dict = json.loads(strava_activity_json)
        strava_activity_id = strava_activity_dict["id"]

        # intercept API call and return local json instead
        httpretty.enable(allow_net_connect=False)
        activity_url = self.STRAVA_BASE_URL + "/activities/%s" % strava_activity_id

        httpretty.register_uri(
            httpretty.GET,
            activity_url,
            content_type="application/json",
            body=strava_activity_json,
            status=200,
        )

        # intercepted call to the API
        strava_activity = self.athlete.strava_client.get_activity(strava_activity_id)

        httpretty.disable()

        return strava_activity

    def test_no_strava_token(self):

        non_strava_user = UserFactory(password="testpassword")
        self.client.login(username=non_strava_user.username, password="testpassword")

        url = reverse("routes:import_strava")
        response = self.client.get(url)

        self.assertRedirects(response, reverse("strava_connect"))

    def test_save_strava_activity_new_manual_activity(self):

        strava_activity = self.load_strava_activity_from_json("manual_activity.json")
        activity = Activity(athlete=self.athlete, strava_id=strava_activity.id)

        # save the manual strava activity
        activity.save_from_strava(strava_activity)

        self.assertEqual(Activity.objects.count(), 1)
        self.assertTrue(activity.manual)
        self.assertEqual(
            str(activity),
            "{}: {} - {}".format(
                activity.activity_type, activity.name, activity.athlete
            ),
        )

    def test_save_strava_race_run(self):

        # load_json and save the manual strava activity
        strava_activity = self.load_strava_activity_from_json("race_run_activity.json")
        activity = Activity(athlete=self.athlete, strava_id=strava_activity.id)
        activity.save_from_strava(strava_activity)
        activity.refresh_from_db()

        self.assertEqual(Activity.objects.count(), 1)
        self.assertEqual(int(activity.workout_type), Activity.RACE_RUN)

        url = "https://www.strava.com/activities/{}".format(activity.strava_id)
        self.assertEqual(url, activity.get_strava_url())
        self.assertAlmostEqual(activity.distance / 1000, activity.get_distance().km)
        self.assertAlmostEqual(activity.totalup, activity.get_totalup().m)

    def test_save_strava_activity_add_existing_gear(self):

        # create activity with no gear
        activity = ActivityFactory(gear=None, athlete=self.athlete)

        # create gear
        gear = GearFactory(athlete=self.athlete)

        # fake activity from Strava with a gear_id from an existing gear
        strava_activity = deepcopy(activity)

        # map id back to strava_id
        strava_activity.id = activity.strava_id

        # map totalup back to total_elevation_gain and activity_type to type
        strava_activity.total_elevation_gain = activity.totalup
        strava_activity.type = activity.activity_type

        #  add existing gear to the Strava activity
        strava_activity.gear_id = gear.strava_id

        # update activity with Strava data
        activity.save_from_strava(strava_activity)

        self.assertEqual(gear, activity.gear)
        self.assertEqual(Activity.objects.count(), 1)
        self.assertEqual(
            str(gear), "{0} - {1}".format(activity.gear.brand_name, activity.gear.name)
        )

    def test_save_strava_activity_add_new_gear(self):

        # create activity with no gear
        activity = ActivityFactory(gear=None, athlete=self.athlete)

        # fake activity from Strava with a new gear_id
        strava_activity = deepcopy(activity)

        # map id back to strava_id
        strava_activity.id = activity.strava_id

        # map totalup back to total_elevation_gain and activity_type to type
        strava_activity.total_elevation_gain = activity.totalup
        strava_activity.type = activity.activity_type

        #  add new gear to the Strava activity
        strava_activity.gear_id = "g123456"

        # intercept Strava API call to get gear info from Strava
        httpretty.enable(allow_net_connect=False)

        gear_url = self.STRAVA_BASE_URL + "/gear/%s" % strava_activity.gear_id
        gear_json = read_data("gear.json", dir_path=CURRENT_DIR)

        httpretty.register_uri(
            httpretty.GET,
            gear_url,
            content_type="application/json",
            body=gear_json,
            status=200,
        )

        # update the activity with strava data: because of the new gear,
        #  it will trigger an update with the Strava API
        activity.save_from_strava(strava_activity)

        httpretty.disable()

        self.assertEqual(strava_activity.gear_id, activity.gear.strava_id)
        self.assertIsInstance(activity.gear, Gear)
        self.assertEqual(Activity.objects.count(), 1)

    def test_save_strava_activity_remove_gear(self):

        # create activity with gear
        activity = ActivityFactory(athlete=self.athlete)

        # fake a Strava activity as it would be retrieved from the API
        strava_activity = deepcopy(activity)

        # map id back to Strava
        strava_activity.id = activity.strava_id

        # map totalup back to total_elevation_gain and activity_type to type
        strava_activity.total_elevation_gain = activity.totalup
        strava_activity.type = activity.activity_type

        # remove gear
        strava_activity.gear_id = None

        # save the strava activity
        activity.save_from_strava(strava_activity)

        self.assertIsNone(activity.gear)
        self.assertEqual(Activity.objects.count(), 1)

    def test_update_strava_activity_deleted(self):

        # create activity
        activity = ActivityFactory(athlete=self.athlete)

        # API response will be a 404 because it was deleted or
        # the the privacy settings have changed
        httpretty.enable(allow_net_connect=False)

        activity_url = self.STRAVA_BASE_URL + "/activities/%s" % activity.strava_id
        not_found_json = read_data("activity_not_found.json", dir_path=CURRENT_DIR)

        httpretty.register_uri(
            httpretty.GET,
            activity_url,
            content_type="application/json",
            body=not_found_json,
            status=404,
        )

        # update the activity from strava data
        activity.update_from_strava()

        httpretty.disable()

        self.assertEqual(Activity.objects.count(), 0)

    def test_update_strava_activity_changed(self):

        strava_activity = self.load_strava_activity_from_json("manual_activity.json")
        activity = Activity(athlete=self.athlete, strava_id=strava_activity.id)

        # save the manual strava activity
        activity.save_from_strava(strava_activity)

        self.assertEqual(activity.description, "Manual Description")

        httpretty.enable(allow_net_connect=False)

        activity_url = self.STRAVA_BASE_URL + "/activities/%s" % activity.strava_id
        changed_json = read_data("manual_activity_changed.json", dir_path=CURRENT_DIR)

        httpretty.register_uri(
            httpretty.GET,
            activity_url,
            content_type="application/json",
            body=changed_json,
            status=200,
        )

        # update the activity from strava data
        activity.update_from_strava()

        httpretty.disable()

        self.assertEqual(Activity.objects.count(), 1)
        self.assertTrue(activity.manual)

        self.assertEqual(activity.description, "")

    def test_import_all_user_activities_from_strava(self):

        httpretty.enable(allow_net_connect=False)
        activities_url = self.STRAVA_BASE_URL + "/athlete/activities"

        # get athlete activities: 2 retrieved
        responses = [
            # first call, content: two activities
            httpretty.Response(
                content_type="application/json",
                body=read_data(
                    "activities.json", dir_path=CURRENT_DIR
                ),  # two activities
            ),
            # second call, content one activity
            httpretty.Response(
                content_type="application/json",
                body=read_data(
                    "activities_one.json", dir_path=CURRENT_DIR
                ),  # one activity
            ),
            httpretty.Response(
                content_type="application/json",
                body=read_data(
                    "activities.json", dir_path=CURRENT_DIR
                ),  # two activities
            ),
            httpretty.Response(content_type="application/json", body="[]"),  # empty
        ]

        httpretty.register_uri(
            httpretty.GET, activities_url, responses=responses, match_querystring=False,
        )

        # update athlete activities: 2 received
        Activity.objects.update_user_activities_from_strava(self.athlete)
        self.assertEqual(Activity.objects.count(), 2)
        # update athlete activities: 1 received
        Activity.objects.update_user_activities_from_strava(self.athlete)
        self.assertEqual(Activity.objects.count(), 1)
        # update athlete activities: 2 received
        Activity.objects.update_user_activities_from_strava(self.athlete)
        self.assertEqual(Activity.objects.count(), 2)
        # update activities: 0 received
        Activity.objects.update_user_activities_from_strava(self.athlete)
        self.assertEqual(Activity.objects.count(), 0)

    def test_get_streams_from_strava_manual_activity(self):
        activity = ActivityFactory(athlete=self.athlete, manual=True)
        self.assertIsNone(activity.get_streams_from_strava())

    def test_get_streams_from_strava_missing_streams(self):
        activity = ActivityFactory(athlete=self.athlete)

        httpretty.enable(allow_net_connect=False)

        STREAM_TYPES = ["time", "altitude", "distance"]
        streams_url = self.STRAVA_BASE_URL + "/activities/%s/streams/%s" % (
            activity.strava_id,
            ",".join(STREAM_TYPES),
        )

        httpretty.register_uri(
            httpretty.GET,
            streams_url,
            content_type="application/json",
            body=read_data("missing_streams.json", dir_path=CURRENT_DIR),
            status=200,
            match_querystring=False,
        )

        raw_streams = activity.get_streams_from_strava()
        httpretty.disable()

        self.assertIsNone(raw_streams)

    def test_get_streams_from_strava_all_streams(self):
        activity = ActivityFactory(athlete=self.athlete)

        httpretty.enable(allow_net_connect=False)

        STREAM_TYPES = ["time", "altitude", "distance"]
        streams_url = self.STRAVA_BASE_URL + "/activities/%s/streams/%s" % (
            activity.strava_id,
            ",".join(STREAM_TYPES),
        )

        httpretty.register_uri(
            httpretty.GET,
            streams_url,
            content_type="application/json",
            body=read_data("streams.json", dir_path=CURRENT_DIR),
            status=200,
            match_querystring=False,
        )

        raw_streams = activity.get_streams_from_strava()
        httpretty.disable()

        self.assertEqual(len(raw_streams), 3)

    @override_settings(STRAVA_VERIFY_TOKEN="RIGHT_TOKEN")
    def test_strava_webhook_callback_url(self):

        # subscritption validation successful
        url = reverse("routes:strava_webhook")
        data = {
            "hub.verify_token": "RIGHT_TOKEN",
            "hub.challenge": "challenge",
            "hub.mode": "subscribe",
        }

        response = self.client.get(url, data)
        self.assertContains(response, data["hub.challenge"])

        # subscription validation with wrong token
        data["hub.verify_token"] = "WRONG_TOKEN"

        response = self.client.get(url, data)
        self.assertEqual(response.status_code, 401)

        # event posted by Strava
        data = json.loads(read_data("event.json", dir_path=CURRENT_DIR))
        response = self.client.post(url, data, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(WebhookTransaction.objects.count(), 1)

        transaction = WebhookTransaction.objects.first()
        self.assertEqual(
            str(transaction),
            "{0} - {1}".format(
                transaction.get_status_display(), transaction.date_generated,
            ),
        )

    def test_process_strava_event_create_new_activity(self):
        transaction = WebhookTransactionFactory()

        # link transaction to athlete
        transaction.body["owner_id"] = self.athlete.strava_id

        # transaction creates a new activty
        transaction.body["aspect_type"] = "create"
        transaction.body["object_type"] = "activity"
        transaction.body["object_id"] = 12345

        transaction.save()

        httpretty.enable(allow_net_connect=False)

        activity_url = (
            self.STRAVA_BASE_URL + "/activities/%s" % transaction.body["object_id"]
        )
        activity_json = read_data("manual_activity.json", dir_path=CURRENT_DIR)

        httpretty.register_uri(
            httpretty.GET,
            activity_url,
            content_type="application/json",
            body=activity_json,
            status=200,
        )

        # process the event
        task = ProcessStravaEvents()
        task.run()

        httpretty.disable()

        activities = Activity.objects.all()
        transactions = WebhookTransaction.objects.all()

        self.assertEqual(activities.count(), 1)
        self.assertEqual(activities.first().strava_id, transaction.body["object_id"])
        self.assertEqual(transactions.first().status, self.PROCESSED)
        self.assertIsNone(transactions.filter(status=self.UNPROCESSED).first())
        self.assertIsNone(transactions.filter(status=self.ERROR).first())
        self.assertIsNone(transactions.filter(status=self.SKIPPED).first())

    def test_process_strava_event_update_existing_activity(self):
        transaction = WebhookTransactionFactory()

        # link transaction to athlete
        transaction.body["owner_id"] = self.athlete.strava_id

        # associate transaction with an existing activity
        strava_id = 12345
        ActivityFactory(strava_id=strava_id)
        transaction.body["aspect_type"] = "update"
        transaction.body["object_type"] = "activity"
        transaction.body["object_id"] = strava_id
        transaction.save()

        httpretty.enable(allow_net_connect=False)

        activity_url = (
            self.STRAVA_BASE_URL + "/activities/%s" % transaction.body["object_id"]
        )
        changed_json = read_data("manual_activity_changed.json", dir_path=CURRENT_DIR)

        httpretty.register_uri(
            httpretty.GET,
            activity_url,
            content_type="application/json",
            body=changed_json,
            status=200,
        )

        # process the event
        task = ProcessStravaEvents()
        task.run()
        httpretty.disable()

        transactions = WebhookTransaction.objects.all()

        self.assertEqual(Activity.objects.count(), 1)
        self.assertEqual(Activity.objects.first().strava_id, strava_id)
        self.assertEqual(transactions.filter(status=self.PROCESSED).count(), 1)
        self.assertIsNone(transactions.filter(status=self.UNPROCESSED).first())
        self.assertIsNone(transactions.filter(status=self.ERROR).first())
        self.assertIsNone(transactions.filter(status=self.SKIPPED).first())

    def test_process_strava_event_delete_existing_activity(self):

        transaction = WebhookTransactionFactory()

        # link transaction to athlete
        transaction.body["owner_id"] = self.athlete.strava_id

        # associate transaction with an existing activity
        strava_id = 12345
        ActivityFactory(strava_id=strava_id)
        transaction.body["aspect_type"] = "delete"
        transaction.body["object_type"] = "activity"
        transaction.body["object_id"] = strava_id
        transaction.save()

        httpretty.enable(allow_net_connect=False)

        # process the event
        task = ProcessStravaEvents()
        task.run()
        httpretty.disable()

        transactions = WebhookTransaction.objects.all()

        self.assertEqual(Activity.objects.count(), 0)
        self.assertEqual(transactions.filter(status=self.PROCESSED).count(), 1)
        self.assertIsNone(transactions.filter(status=self.UNPROCESSED).first())
        self.assertIsNone(transactions.filter(status=self.ERROR).first())
        self.assertIsNone(transactions.filter(status=self.SKIPPED).first())

    def test_process_strava_event_missing_user(self):
        transaction = WebhookTransactionFactory()

        # link transaction to inexistant athlete
        transaction.body["owner_id"] = 666
        transaction.save()

        httpretty.enable(allow_net_connect=False)

        # process the event
        task = ProcessStravaEvents()
        task.run()

        httpretty.disable()

        transactions = WebhookTransaction.objects.all()

        self.assertEqual(transactions.filter(status=self.ERROR).count(), 1)
        self.assertIsNone(transactions.filter(status=self.PROCESSED).first())
        self.assertIsNone(transactions.filter(status=self.UNPROCESSED).first())
        self.assertIsNone(transactions.filter(status=self.SKIPPED).first())

    def test_process_strava_skip_duplicate_events(self):
        transaction1 = WebhookTransactionFactory()

        # link transaction to athlete
        transaction1.body["owner_id"] = self.athlete.strava_id

        # associate transaction with an existing activity
        strava_id = 12345
        ActivityFactory(strava_id=strava_id)
        transaction1.body["aspect_type"] = "create"
        transaction1.body["object_type"] = "activity"
        transaction1.body["object_id"] = strava_id
        transaction1.save()

        transaction2 = WebhookTransactionFactory(
            date_generated=transaction1.date_generated + timedelta(minutes=1)
        )
        transaction2.body["aspect_type"] = "update"
        transaction2.body["object_type"] = "activity"
        transaction2.body["object_id"] = strava_id
        transaction2.save()

        httpretty.enable(allow_net_connect=False)

        activity_url = self.STRAVA_BASE_URL + "/activities/%s" % strava_id
        changed_json = read_data("manual_activity_changed.json", dir_path=CURRENT_DIR)

        httpretty.register_uri(
            httpretty.GET,
            activity_url,
            content_type="application/json",
            body=changed_json,
            status=200,
        )

        # process the event
        task = ProcessStravaEvents()
        task.run()

        httpretty.disable()

        transactions = WebhookTransaction.objects.all()

        self.assertEqual(transactions.filter(status=self.PROCESSED).count(), 1)
        self.assertEqual(
            transactions.filter(status=self.PROCESSED).first().body["aspect_type"],
            "update",
        )
        self.assertIsNone(transactions.filter(status=self.UNPROCESSED).first())
        self.assertIsNone(transactions.filter(status=self.ERROR).first())
        self.assertEqual(transactions.filter(status=self.SKIPPED).count(), 1)

    def test_import_all_activities_from_strava(self):
        import_url = reverse("routes:import_strava")

        with patch(
            "homebytwo.routes.tasks.import_athlete_strava_activities.delay"
        ) as mock_task:
            response = self.client.get(import_url)
            self.assertRedirects(response, reverse("routes:activities"))
            self.assertTrue(mock_task.called)

    def test_view_activity_list_empty(self):
        activity_list_url = reverse("routes:activities")
        response = self.client.get(activity_list_url)

        self.assertEqual(response.status_code, 200)