import os

import factory
import factory.django
import factory.fuzzy
from django.contrib.gis.geos import GEOSGeometry
from pandas import read_json

from ...routes import models
from ...utils.factories import UserFactory


def load_data(file):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        data_dir = 'data'

        json_path = os.path.join(
            dir_path,
            data_dir,
            file,
        )

        return open(json_path).read()


class ActivityTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.ActivityType
    name = factory.fuzzy.FuzzyText()
    slope_squared_param = factory.fuzzy.FuzzyFloat(3.0, 10.0)
    slope_param = factory.fuzzy.FuzzyFloat(0.2, 1.2)
    flat_param = factory.fuzzy.FuzzyFloat(0.20, 1.0)
    total_elevation_gain_param = factory.fuzzy.FuzzyFloat(0.05, 1.05)


class PlaceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Place

    place_type = factory.Iterator(
        models.Place.PLACE_TYPE_CHOICES,
        getter=lambda c: c[0]
    )
    name = factory.fuzzy.FuzzyText()
    description = factory.fuzzy.FuzzyText(length=100)
    altitude = factory.fuzzy.FuzzyInteger(5000)
    public_transport = factory.Iterator([True, False])
    geom = GEOSGeometry('POINT(0 0)', srid=21781)


class RouteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = models.Route
        exclude = ('route_geojson', 'route_data_json')

    route_geojson = load_data('route_geom.json')
    route_data_json = load_data('route_data.json')

    activity_type = factory.SubFactory(ActivityTypeFactory)
    name = factory.fuzzy.FuzzyText()
    source_id = factory.Sequence(lambda n: '%d' % n)
    data_source = 'homebytwo'
    description = factory.fuzzy.FuzzyText(length=100)
    owner = factory.SubFactory(UserFactory)
    totalup = factory.fuzzy.FuzzyInteger(5000)
    totaldown = factory.fuzzy.FuzzyInteger(5000)
    length = factory.fuzzy.FuzzyInteger(50000)
    geom = GEOSGeometry(route_geojson, srid=21781)
    start_place = factory.SubFactory(
        PlaceFactory,
        geom='POINT (%s %s)' % geom.coords[0]
    )
    end_place = factory.SubFactory(
        PlaceFactory,
        geom='POINT (%s %s)' % geom.coords[-1]
    )
    data = read_json(route_data_json, orient='records')