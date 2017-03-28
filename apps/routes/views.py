from django.contrib.auth.decorators import login_required
from django.contrib.gis.measure import D
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic.edit import UpdateView, DeleteView

from .models import Route, RoutePlace


def routes(request):
    routes = Route.objects.order_by('name')
    context = {
        'routes': routes,
    }

    return render(request, 'routes/routes.html', context)


def route(request, pk):
    # load route from Database
    route = Route.objects.select_related('start_place', 'end_place').get(id=pk)

    # retrieve checkpoints along the way and enrich them with data
    places = RoutePlace.objects.select_related('route', 'place').\
        filter(route=pk)

    for place in places:
        place.schedule = route.get_time_data(place.line_location, 'schedule')
        place.altitude = place.get_altitude()
        place.distance = D(m=place.line_location * route.length)

    # enrich start and end place with data
    if route.start_place_id:
        route.start_place.schedule = route.get_time_data(0, 'schedule')
        route.start_place.altitude = route.get_distance_data(0, 'altitude')
    if route.end_place_id:
        route.end_place.schedule = route.get_time_data(1, 'schedule')
        route.end_place.altitude = route.get_distance_data(1, 'altitude')

    context = {
        'route': route,
        'places': places
    }
    return render(request, 'routes/route.html', context)


@method_decorator(login_required, name='dispatch')
class ImageFormView(UpdateView):
    """
    Playing around with class based views.
    """
    model = Route
    fields = ['image']
    template_name_suffix = '_image_form'


@method_decorator(login_required, name='dispatch')
class RouteDelete(DeleteView):
    """
    Playing around with class based views.
    """
    model = Route
    success_url = reverse_lazy('routes:routes')


@method_decorator(login_required, name='dispatch')
class RouteEdit(UpdateView):
    model = Route
    fields = ['name', 'description', 'image']