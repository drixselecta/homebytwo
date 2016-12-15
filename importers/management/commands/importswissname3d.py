from django.core.management.base import BaseCommand, CommandError

import os
from ...models import Swissname3dPlace
from django.contrib.gis.utils import LayerMapping
from django.contrib.gis.gdal import DataSource


class Command(BaseCommand):

    help = 'Import from the SwissNAME3D points shapefile to the Place Model'

    def add_arguments(self, parser):

        # path to the shapefile
        parser.add_argument(
            'shapefile', type=str,
            help='Path to the shapefile to import. '
        )

        # Limit to number of places
        parser.add_argument(
            '--limit', type=int,
            nargs='?', default=-1,
            help=(
                  'Limits the number of imported features. '
            ),
        )

        # Deletes all existing SwissNAME3D places
        parser.add_argument(
            '--delete', '--drop',
            action='store_true', dest='delete', default=False,
            help=(
                'Deletes all existing SwissNAME3D places before the import. '
            ),
        )

        # runs without asking any questions
        parser.add_argument(
            '--noinput', '--no-input',
            action='store_false', dest='interactive', default=True,
            help=(
                'Tells Django to NOT prompt the user for input of any kind. '
            ),
        )

    def handle(self, *args, **options):

        # Generate path and make sure the file exists
        shapefile = os.path.abspath(options['shapefile'])
        if not os.path.exists(shapefile):
            error_msg = ('The file "%s" could not be found.' % shapefile)
            raise FileNotFoundError(error_msg)

        # Define mapping between layer fields of the shapefile
        # and fields of Place Model
        swissname3d_mapping = {
            'place_type': 'OBJEKTART',
            'altitude': 'HOEHE',
            'name': 'NAME',
            'geom': 'POINT25D',
            'source_id': 'UUID',
        }

        # Try to map the data
        try:
            layermapping = LayerMapping(
                Swissname3dPlace, shapefile, swissname3d_mapping,
                transform=False, encoding='UTF-8',
            )

        except:
            error_msg = (
                'The shapefile could not be interpreted.\nAre you sure '
                '"%s" is the SwissNAME3D_PKT shapefile?' % shapefile
            )
            raise CommandError(error_msg)

        # Get the number of features
        datasource = DataSource(shapefile)
        layer = datasource[0]
        feature_count = len(layer)

        # Display number of features to import
        limit = options['limit']
        if limit > -1:
            feature_count = min(feature_count, limit)

        # Save the mapped data to the Database
        if options['interactive']:
            self.stdout.write(
                'Saving %d places from %s' % (feature_count, shapefile)
            )

        layermapping.save(strict=True, fid_range=(0, feature_count),
                          stream=self.stdout, progress=True)

        # Inform on success
        msg = 'Successfully imported %d places.' % feature_count
        self.stdout.write(self.style.SUCCESS(msg))
