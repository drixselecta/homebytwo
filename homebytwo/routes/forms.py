from django.forms import BooleanField, ModelChoiceField, ModelForm

from .models import Place, Route, RoutePlace


class RouteForm(ModelForm):

    def __init__(self, *args, **kwargs):
        super(RouteForm, self).__init__(*args, **kwargs)

        # add Kanbasu 2 class for form fields
        select_fields = ['activity_type', 'start_place', 'end_place']
        for field in select_fields:
            self.fields[field].widget.attrs.update({'class': 'field'})

    class PlaceChoiceField(ModelChoiceField):
        def label_from_instance(self, obj):
            return '%s - %s, %d meters away.' % (
                obj.name,
                obj.get_place_type_display(),
            )

    start_place = PlaceChoiceField(
        queryset=Place.objects.all(),
        empty_label=None,
        required=False,
    )

    end_place = PlaceChoiceField(
        queryset=Place.objects.all(),
        empty_label=None,
        required=False,
    )

    class Meta:
        model = Route
        fields = [
            'activity_type',
            'data',
            'end_place',
            'geom',
            'length',
            'name',
            'source_id',
            'start_place',
            'totaldown',
            'totalup',
        ]


class RoutePlaceForm(ModelForm):
    class Meta:
        model = RoutePlace
        fields = ['place', 'line_location', 'altitude_on_route', 'include']

    include = BooleanField(
        required=False,
        initial=True,
    )

    # Kanbasu 2 class for form checkboxes
    include.widget.attrs.update({'class': 'checkbox'})
