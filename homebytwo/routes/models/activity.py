from abc import abstractmethod
from typing import List, Optional

from django.contrib.gis.db import models
from django.contrib.gis.measure import D
from django.core.exceptions import FieldError
from django.db.models import Count

from numpy import array
from pandas import DataFrame
from stravalib import unithelper
from stravalib.exc import ObjectNotFound

from ...core.models import TimeStampedModel
from ..fields import DataFrameField, NumpyArrayField
from ..prediction_model import PredictionModel

STREAM_TYPES = ["time", "altitude", "distance", "moving"]
STRAVA_ACTIVITY_URL = "https://www.strava.com/activities/{}"


def athlete_streams_directory_path(instance, filename):
    # streams will upload to MEDIA_ROOT/athlete_<id>/<filename>
    return f"athlete_{instance.athlete.id}/streams/{filename}"


def get_default_array():
    """
    default array (mutable) for the `regression_coefficients` NumpyArrayField.
    """
    return array([0.0, 0.0, 0.0, 0.075, 0.0004, 0.0001, 0.0001]).copy()


def get_default_category():
    """
    default list (mutable) for the categories saved by the one-hot encoder ArrayField.
    """
    return array(["None"]).copy()


def update_user_activities_from_strava(athlete, after=None, before=None, limit=1000):
    """
    fetches an athlete's activities from Strava and saves them to the Database.
    It erases the ones that are no more available because they have been deleted
    or set to private and returns all of the athlete's current activities.

    Parameters:
    'after': start date after specified value (UTC). datetime.datetime, str or None.
    'before': start date before specified value (UTC). datetime.datetime or str or None
    'limit': maximum activities retrieved. Integer

    See https://pythonhosted.org/stravalib/usage/activities.html#list-of-activities and
    https://developers.strava.com/playground/#/Activities/getLoggedInAthleteActivities
    """

    # retrieve the athlete's activities on Strava
    strava_activities = athlete.strava_client.get_activities(
        before=before, after=after, limit=limit
    )

    current_activities = []
    for strava_activity in strava_activities:
        if is_activity_supported(strava_activity):
            activity = Activity.get_or_stub(strava_activity.id, athlete)
            activity.update_with_strava_data(strava_activity)
            current_activities.append(activity)

    # delete existing activities that are not in the Strava result
    existing_activities = Activity.objects.filter(athlete=athlete)
    existing_activities.exclude(
        id__in=[activity.id for activity in current_activities]
    ).delete()

    return current_activities


def is_activity_supported(strava_activity):
    """
    check that the activity was not manually uploaded by the athlete
    and if the activity type is supported by homebytwo
    """
    if strava_activity.manual:
        return False
    if strava_activity.type not in ActivityType.SUPPORTED_ACTIVITY_TYPES:
        return False
    return True


def are_streams_valid(strava_streams):
    """
    check if all required stream types are present and
    if they all contain values.
    """
    if not all(stream_type in strava_streams for stream_type in STREAM_TYPES):
        return False
    if not all(raw_stream.original_size > 0 for raw_stream in strava_streams.values()):
        return False
    return True


class ActivityQuerySet(models.QuerySet):
    def for_user(self, user):
        """
        return all routes of a given user.
        this is convenient with the 'request.user' object in views.
        """
        return self.filter(athlete=user.athlete)


class ActivityManager(models.Manager):
    def get_queryset(self):
        return ActivityQuerySet(self.model, using=self._db)

    def for_user(self, user):
        return self.get_queryset().for_user(user)


class Activity(TimeStampedModel):
    """
    An athlete's Strava activity used to train his prediction models
    """

    NONE = None
    DEFAULT_RUN = 0
    RACE_RUN = 1
    LONG_RUN = 2
    WORKOUT_RUN = 3
    DEFAULT_RIDE = 10
    RACE_RIDE = 11
    WORKOUT_RIDE = 12

    WORKOUT_TYPE_CHOICES = [
        (NONE, "None"),
        (DEFAULT_RUN, "default run"),
        (RACE_RUN, "race run"),
        (LONG_RUN, "long run"),
        (WORKOUT_RUN, "workout run"),
        (DEFAULT_RIDE, "default ride"),
        (RACE_RIDE, "race ride"),
        (WORKOUT_RIDE, "workout ride"),
    ]

    # name of the activity as imported from Strava
    name = models.CharField(max_length=255)

    # description of the activity as imported from Strava
    description = models.TextField(blank=True)

    # Activity ID on Strava
    strava_id = models.BigIntegerField(unique=True)

    # Starting date and time of the activity in UTC
    start_date = models.DateTimeField()

    # Athlete whose activities have been imported from Strava
    athlete = models.ForeignKey(
        "Athlete", on_delete=models.CASCADE, related_name="activities"
    )

    # Athlete whose activities have been imported from Strava
    activity_type = models.ForeignKey(
        "ActivityType", on_delete=models.PROTECT, related_name="activities"
    )

    # Total activity distance
    distance = models.FloatField("Activity distance in m", blank=True, null=True)

    # elevation gain in m
    total_elevation_gain = models.FloatField(
        "Total elevation gain in m", blank=True, null=True
    )

    # total duration of the activity in seconds as opposed to moving time
    elapsed_time = models.DurationField(
        "Total activity time as timedelta", blank=True, null=True
    )

    # time in movement during the activity
    moving_time = models.DurationField(
        "Movement time as timedelta", blank=True, null=True
    )

    # streams retrieved from the Strava API
    streams = DataFrameField(
        null=True, upload_to=athlete_streams_directory_path, unique_fields=["strava_id"]
    )

    # skip trying to import streams from Strava
    skip_streams_import = models.BooleanField(default=False)

    # Workout Type as defined in Strava
    workout_type = models.SmallIntegerField(
        choices=WORKOUT_TYPE_CHOICES, blank=True, null=True
    )

    # is the activity flagged as a commute?
    commute = models.BooleanField(default=False)

    # Gear used if any
    gear = models.ForeignKey(
        "Gear",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="activities",
    )

    class Meta:
        ordering = ["-start_date"]
        verbose_name_plural = "activities"

    # Custom manager
    objects = ActivityManager()

    def __str__(self):
        return "{0}: {1} - {2}".format(self.activity_type, self.name, self.athlete)

    def get_strava_url(self):
        # return the absolute URL to the activity on Strava
        return STRAVA_ACTIVITY_URL.format(self.strava_id)

    def get_distance(self):
        # return the activity distance as a Distance object
        return D(m=self.distance)

    def get_total_elevation_gain(self):
        # return the activity distance as a Distance object
        return D(m=self.total_elevation_gain)

    @classmethod
    def get_or_stub(cls, strava_id, athlete):
        """
        use Strava id to return an activity from the database or an activity stub
        """
        try:
            activity = cls.objects.get(strava_id=strava_id)
        except cls.DoesNotExist:
            activity = cls(strava_id=strava_id, athlete=athlete)

        return activity

    def get_activity_from_strava(self):
        """
        retrieve single activity information from Strava.
        """
        try:
            strava_activity = self.athlete.strava_client.get_activity(self.strava_id)

        # Activity was was deleted or made private on Strava
        except ObjectNotFound:
            if self.id:
                self.delete()

        # strava activity was found on Strava
        else:
            return strava_activity

    def update_with_strava_data(self, strava_activity, commit=True):
        """
        update an activity based on information received from Strava.

        :param strava_activity: the activity object returned by the Strava API client.
        :param commit: save Strava activity to the database
        """

        # fields from the Strava API object mapped to the Activity Model
        fields_map = {
            "name": strava_activity.name,
            "activity_type": strava_activity.type,
            "start_date": strava_activity.start_date,
            "elapsed_time": strava_activity.elapsed_time,
            "moving_time": strava_activity.moving_time,
            "description": strava_activity.description,
            "workout_type": strava_activity.workout_type,
            "distance": unithelper.meters(strava_activity.distance),
            "total_elevation_gain": unithelper.meters(
                strava_activity.total_elevation_gain
            ),
            "gear": strava_activity.gear_id,
            "commute": strava_activity.commute,
        }

        # find or create the activity type
        fields_map["activity_type"], created = ActivityType.objects.get_or_create(
            name=strava_activity.type
        )

        if strava_activity.gear_id:
            # resolve foreign key relationship for gear and get gear info if new
            fields_map["gear"], created = Gear.objects.get_or_create(
                strava_id=strava_activity.gear_id, athlete=self.athlete
            )
            if created:
                fields_map["gear"].update_from_strava()

        # transform description text to empty if None
        if strava_activity.description is None:
            fields_map["description"] = ""

        # update activity information
        for key, value in fields_map.items():
            setattr(self, key, value)

        if commit:
            self.save()

    def update_activity_streams_from_strava(self):
        """
        save activity streams from Strava in a pandas DataFrame.
        returns True if streams could be imported.
        """
        strava_streams = self.get_streams_from_strava()

        if strava_streams and are_streams_valid(strava_streams):
            self.streams = DataFrame(
                {key: stream.data for key, stream in strava_streams.items()}
            )
            self.save(update_fields=["streams"])
            return True

        # otherwise, skip trying to get the streams next time
        self.skip_streams_import = True
        self.save(update_fields=["skip_streams_import"])
        return False

    def get_streams_from_strava(self, resolution="low"):
        """
        Return activity streams from Strava: Time, Altitude, Distance and Moving.

        Only activities with all four required types of stream present will be returned.
        Setting a 'low' resolution provides free downsampling of the data
        for better accuracy in the prediction.
        """

        strava_client = self.athlete.strava_client
        return strava_client.get_activity_streams(
            self.strava_id, types=STREAM_TYPES, resolution=resolution
        )

    def get_training_data(self):
        """
        return activity data for training the linear regression model.
        """

        # load activity streams as a DataFrame
        activity_data = self.streams

        # calculate gradient in percents, pace in minutes/kilometer and
        # cumulative elevation gain
        activity_data["step_distance"] = activity_data.distance.diff()
        activity_data["gradient"] = (
            activity_data.altitude.diff() / activity_data.step_distance * 100
        )
        activity_data["pace"] = activity_data.time.diff() / activity_data.step_distance
        activity_data["cumulative_elevation_gain"] = activity_data.altitude.diff()[
            activity_data.altitude.diff() >= 0
        ].cumsum()
        activity_data[
            "cumulative_elevation_gain"
        ] = activity_data.cumulative_elevation_gain.fillna(method="ffill").fillna(
            value=0
        )

        # remove rows with empty gradient or empty pace
        columns = ["gradient", "pace"]
        activity_data = activity_data[activity_data[columns].notnull().all(1)].copy()

        # add activity information to every row
        activity_properties = {
            "strava_id": self.strava_id,
            "start_date": self.start_date,
            "total_elevation_gain": self.total_elevation_gain,
            "total_distance": self.distance,
            "gear": self.gear.strava_id if self.gear else "None",
            "workout_type": self.get_workout_type_display()
            if self.workout_type or self.workout_type == 0
            else "None",
            "commute": self.commute,
        }

        return activity_data.assign(
            **{key: value for key, value in activity_properties.items()}
        )


class PredictedModel(models.Model):
    """
    base Model for training and persisting schedule prediction models

    Subclassed by ActivityType and ActivityPerformance.
    """

    # list of regression coefficients as trained by the regression model
    regression_coefficients = NumpyArrayField(
        models.FloatField(), default=get_default_array
    )

    # flat pace in seconds per meter: the intercept of the regression
    flat_parameter = models.FloatField(default=0.36)  # 6:00/km or 10km/h

    # workout_type categories found by the prediction model
    workout_type_categories = NumpyArrayField(
        models.CharField(max_length=50),
        default=get_default_category,
    )

    # reliability and cross_validation scores of the prediction model
    # between 0.0 and 1.0
    model_score = models.FloatField(default=0.0)
    cv_scores = NumpyArrayField(models.FloatField(), default=get_default_array)

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        """
        set activity_type and adapt to the number of categorical columns.

        self._activity_type is required to remove outliers in the training data based
        on max and min speed and gradient.

        categorical columns determines the shape of the regression_coefficients array
        """
        super().__init__(*args, **kwargs)

        # set _activity_type to self or related Model
        if hasattr(self, "activity_type"):
            self._activity_type = self.activity_type
        elif isinstance(self, ActivityType):
            self._activity_type = self
        else:
            raise FieldError(f"Cannot find activity_type for {self}")

        # set default value for regression_coefficients based on the number of
        # categorical columns present in the Model
        categorical_coefficients = [0.0] * len(self.get_categorical_columns())
        numerical_coefficients = [0.0, 0.075, 0.0004, 0.0001, 0.0001]
        coefficients = self._meta.get_field("regression_coefficients")
        coefficients.default = array(categorical_coefficients + numerical_coefficients)

    @abstractmethod
    def get_training_activities(self, max_num_activities: Optional[int]):
        """
        retrieve activities to train the prediction model

        must be implemented in the subclasses.
        """
        raise NotImplementedError

    def get_training_data(self, limit_activities: Optional[int] = None) -> DataFrame:
        """
        retrieve training data for the prediction model

        :param limit_activities: maximum number of Strava activities used to feed the
        prediction model, defaults to `None`, i.e. all available activities
        """
        target_activities = self.get_training_activities(limit_activities)

        # collect activity_data into a pandas DataFrame
        observations = DataFrame()
        for activity in target_activities:
            observations = observations.append(
                activity.get_training_data(), sort=True, ignore_index=True
            )

        return observations

    def remove_outliers(self, observations):
        """
        remove speed and gradient outliers from training data based on ActivityType
        """
        return observations[
            (observations.pace > self._activity_type.min_pace)
            & (observations.pace < self._activity_type.max_pace)
            & (observations.gradient > self._activity_type.min_gradient)
            & (observations.gradient < self._activity_type.max_gradient)
        ]

    @classmethod
    def get_categorical_columns(cls) -> List[str]:
        """
        determine columns to use for categorical data based on available Model fields

        ActivityPerformance has two fields: gear_categories, workout_type_categories
        ActivityType has one: workout_type_categories
        """
        possible_columns = ["gear", "workout_type"]
        return list(filter(lambda c: hasattr(cls, f"{c}_categories"), possible_columns))

    def train_prediction_model(self, limit_activities: Optional[int] = None) -> str:
        """
        train prediction model for ActivityType or ActivityPerformance

        :param limit_activities: max number of activities considered for training
        :return: description of the training result
        """

        observations = self.get_training_data(limit_activities=limit_activities)
        if observations.empty:
            return (
                f"No training data found for activity type: {self._activity_type.name}"
            )

        # remove outliers
        data = self.remove_outliers(observations)

        # determine categorical columns for model training
        categorical_columns = self.get_categorical_columns()

        # train prediction model
        prediction_model = PredictionModel(categorical_columns=categorical_columns)
        feature_columns = (
            prediction_model.numerical_columns + prediction_model.categorical_columns
        )
        prediction_model.train(
            y=data["pace"],
            x=data[feature_columns].fillna(value="None"),
        )

        # save model score
        self.model_score = prediction_model.model_score
        self.cv_scores = prediction_model.cv_scores

        # save coefficients and intercept
        regression = prediction_model.pipeline.named_steps["linearregression"]
        self.regression_coefficients = regression.coef_
        self.flat_parameter = regression.intercept_

        # save categories from categorical columns
        for index, column in enumerate(prediction_model.categorical_columns):
            setattr(
                self,
                f"{column}_categories",
                prediction_model.onehot_encoder_categories[index],
            )

        self.save()

        message = (
            f"{self} successfully trained with {data.shape[0]} observations. "
            f"Model score: {self.model_score}, "
            f"cross-validation score: {self.cv_scores}. "
        )
        return message

    def get_prediction_model(self) -> PredictionModel:
        """
        restore the Prediction Model from the saved parameters
        """

        # retrieve categorical columns and values
        categorical_columns = self.get_categorical_columns()
        onehot_encoder_categories = []
        for column in categorical_columns:
            onehot_encoder_categories.append(getattr(self, column + "_categories"))

        return PredictionModel(
            regression_intercept=self.flat_parameter,
            regression_coefficients=self.regression_coefficients,
            categorical_columns=categorical_columns,
            onehot_encoder_categories=onehot_encoder_categories,
        )


class ActivityTypeQuerySet(models.QuerySet):
    def predicted(self):
        """
        retrieve athlete activity_type choices available for schedule prediction
        """
        activity_types = self.filter(name__in=ActivityType.SUPPORTED_ACTIVITY_TYPES)
        activity_types = activity_types.exclude(activities=None)
        activity_types = activity_types.annotate(num_activities=Count("activities"))
        return activity_types.order_by("-num_activities")

    def for_athlete(self, athlete):
        """
        retrieve activity_type choices available for schedule prediction
        """
        return self.predicted().filter(activities__athlete=athlete)


class ActivityType(PredictedModel):
    """
    ActivityType is used to define default performance values for each type of activity.
    The choice of available activities is limited to the ones available on Strava:
    http://developers.strava.com/docs/reference/#api-models-ActivityType
    """

    # Strava activity types
    ALPINESKI = "AlpineSki"
    BACKCOUNTRYSKI = "BackcountrySki"
    CANOEING = "Canoeing"
    CROSSFIT = "Crossfit"
    EBIKERIDE = "EBikeRide"
    ELLIPTICAL = "Elliptical"
    GOLF = "Golf"
    HANDCYCLE = "Handcycle"
    HIKE = "Hike"
    ICESKATE = "IceSkate"
    INLINESKATE = "InlineSkate"
    KAYAKING = "Kayaking"
    KITESURF = "Kitesurf"
    NORDICSKI = "NordicSki"
    RIDE = "Ride"
    ROCKCLIMBING = "RockClimbing"
    ROLLERSKI = "RollerSki"
    ROWING = "Rowing"
    RUN = "Run"
    SAIL = "Sail"
    SKATEBOARD = "Skateboard"
    SNOWBOARD = "Snowboard"
    SNOWSHOE = "Snowshoe"
    SOCCER = "Soccer"
    STAIRSTEPPER = "StairStepper"
    STANDUPPADDLING = "StandUpPaddling"
    SURFING = "Surfing"
    SWIM = "Swim"
    VELOMOBILE = "Velomobile"
    VIRTUALRIDE = "VirtualRide"
    VIRTUALRUN = "VirtualRun"
    WALK = "Walk"
    WEIGHTTRAINING = "WeightTraining"
    WHEELCHAIR = "Wheelchair"
    WINDSURF = "Windsurf"
    WORKOUT = "Workout"
    YOGA = "Yoga"

    ACTIVITY_NAME_CHOICES = [
        (ALPINESKI, "Alpine Ski"),
        (BACKCOUNTRYSKI, "Backcountry Ski"),
        (CANOEING, "Canoeing"),
        (CROSSFIT, "Crossfit"),
        (EBIKERIDE, "E-Bike Ride"),
        (ELLIPTICAL, "Elliptical"),
        (GOLF, "Golf"),
        (HANDCYCLE, "Handcycle"),
        (HIKE, "Hike"),
        (ICESKATE, "Ice Skate"),
        (INLINESKATE, "Inline Skate"),
        (KAYAKING, "Kayaking"),
        (KITESURF, "Kitesurf"),
        (NORDICSKI, "Nordic Ski"),
        (RIDE, "Ride"),
        (ROCKCLIMBING, "Rock Climbing"),
        (ROLLERSKI, "Roller Ski"),
        (ROWING, "Rowing"),
        (RUN, "Run"),
        (SAIL, "Sail"),
        (SKATEBOARD, "Skateboard"),
        (SNOWBOARD, "Snowboard"),
        (SNOWSHOE, "Snowshoe"),
        (SOCCER, "Soccer"),
        (STAIRSTEPPER, "Stair Stepper"),
        (STANDUPPADDLING, "Stand-Up Paddling"),
        (SURFING, "Surfing"),
        (SWIM, "Swim"),
        (VELOMOBILE, "Velomobile"),
        (VIRTUALRIDE, "Virtual Ride"),
        (VIRTUALRUN, "Virtual Run"),
        (WALK, "Walk"),
        (WEIGHTTRAINING, "Weight Training"),
        (WHEELCHAIR, "Wheelchair"),
        (WINDSURF, "Windsurf"),
        (WORKOUT, "Workout"),
        (YOGA, "Yoga"),
    ]

    SUPPORTED_ACTIVITY_TYPES = {
        BACKCOUNTRYSKI,
        EBIKERIDE,
        HANDCYCLE,
        HIKE,
        INLINESKATE,
        NORDICSKI,
        RIDE,
        ROCKCLIMBING,
        ROLLERSKI,
        RUN,
        SNOWSHOE,
        VELOMOBILE,
        VIRTUALRIDE,
        VIRTUALRUN,
        WALK,
        WHEELCHAIR,
    }

    name = models.CharField(max_length=24, choices=ACTIVITY_NAME_CHOICES, unique=True)

    # min and max plausible gradient and speed to filter outliers in activity data.
    min_pace = models.FloatField(default=0.1)  # 1:40/km or 36 km/h
    max_pace = models.FloatField(default=2.4)  # 40:00/km or 1.5 km/h
    min_gradient = models.FloatField(default=-100.0)  # 100% or -45°
    max_gradient = models.FloatField(default=100.0)  # 100% or 45°

    objects = ActivityTypeQuerySet.as_manager()

    def __str__(self):
        return self.name

    def get_training_activities(self, limit=None):
        """
        retrieve Strava activities to train the prediction model
        """
        return self.activities.filter(streams__isnull=False)[:limit]


class ActivityPerformance(PredictedModel, TimeStampedModel):
    """
    Athlete prediction model for an activity type calculated from his Strava history.

    Based on the athlete's past activities on strava, we train a linear regression model
    to predict the athlete's pace on a route. The pace of the athlete depends on the
    *slope* of the travelled segment.
    """

    athlete = models.ForeignKey(
        "Athlete", on_delete=models.CASCADE, related_name="performances"
    )
    activity_type = models.ForeignKey(
        "ActivityType", on_delete=models.PROTECT, related_name="performances"
    )
    # gear categories returned by the prediction model
    gear_categories = NumpyArrayField(
        models.CharField(max_length=50),
        default=get_default_category,
    )

    def __str__(self):
        return "{} - {} - {:.2%}".format(
            self.athlete.user.username, self.activity_type.name, self.model_score
        )

    def get_training_activities(self, limit: int = None):
        """
        return the activities that should feed the prediction model

        :param limit: maximum number of activities considered
        """
        return self.activity_type.activities.filter(
            athlete=self.athlete, streams__isnull=False
        )[:limit]


class Gear(models.Model):
    """
    Small helper model to save gear from Strava.
    """

    strava_id = models.CharField(max_length=24, unique=True)
    name = models.CharField(max_length=100, blank=True)
    brand_name = models.CharField(max_length=100, blank=True)
    athlete = models.ForeignKey(
        "Athlete", on_delete=models.CASCADE, related_name="gears"
    )

    def __str__(self):
        return "{0} - {1}".format(self.brand_name, self.name)

    def update_from_strava(self):
        # retrieve gear info from Strava
        strava_gear = self.athlete.strava_client.get_gear(self.strava_id)

        self.name = strava_gear.name
        if strava_gear.brand_name is not None:
            self.brand_name = strava_gear.brand_name

        # save
        self.save()
