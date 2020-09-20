from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from ..routes.forms import RouteForm
from ..routes.models import Route
from .decorators import remote_connection
from .forms import SwitzerlandMobilityLogin, GpxUploadForm
from .utils import get_route_class_from_data_source, save_detail_forms, split_routes


@login_required
def index(request):
    return render(request, "importers/index.html")


@login_required
@remote_connection
def import_routes(request, data_source):
    """
    retrieve the athlete's list of routes on Strava
    """

    template = "importers/routes.html"

    # retrieve route class from data source in url
    route_class = get_route_class_from_data_source(data_source)

    # retrieve remote routes list
    remote_routes = route_class.objects.get_remote_routes_list(
        athlete=request.user.athlete,
        cookies=request.session.get("switzerland_mobility_cookies"),
    )

    # retrieve the athlete's list of routes already saved in homebytwo
    local_routes = route_class.objects.for_user(request.user)

    # split routes in 3 lists
    new_routes, existing_routes, deleted_routes = split_routes(
        remote_routes, local_routes
    )

    context = {
        "new_routes": new_routes,
        "existing_routes": existing_routes,
        "deleted_routes": deleted_routes,
        "data_source_name": route_class.DATA_SOURCE_NAME,
        "data_source_link": route_class.DATA_SOURCE_LINK,
    }

    return render(request, template, context)


@login_required
@remote_connection
def import_route(request, data_source, source_id):
    """
    import routes from external sources

    There is a modelform for the route with custom __init__ and save methods
    to find available checkpoints and save the ones selected by the athlete
    to the route.
    """

    template = "routes/route_form.html"

    # retrieve route class from data source in url
    route_class = get_route_class_from_data_source(data_source)

    # instantiate route stub with athlete and source_id from url
    route = route_class(athlete=request.user.athlete, source_id=source_id)

    # fetch route details from Remote API
    route.get_route_details(request.session.get("switzerland_mobility_cookies"))
    route.update_track_details_from_data()

    if request.method == "POST":
        # populate checkpoints_formset with POST data
        route_form = RouteForm(request.POST, instance=route)

        # validate forms and save the route and places
        new_route = save_detail_forms(request, route_form)

        # Success! redirect to the page of the newly imported route
        if new_route:
            message = "Route imported successfully from {}".format(
                route_class.DATA_SOURCE_NAME
            )
            messages.success(request, message)
            return redirect("routes:route", pk=new_route.id)

    if request.method == "GET":

        # populate the route_form with route details
        route_form = RouteForm(instance=route)

    context = {
        "object": route,
        "form": route_form,
    }

    return render(request, template, context)


@login_required
@require_POST
def upload_gpx(request):
    """
    Create a new route from GPX information, save it, and redirect to the import route.
    """
    form = GpxUploadForm(request.POST, files=request.FILES)

    if form.is_valid():
        route = form.save(commit=False)
        route.athlete = request.user.athlete
        route.save()
        return redirect("import_existing_route", route_id=route.pk)

    # FIXME return a 400 if this route is called from JS or show the form with errors
    return HttpResponse("Invalid form")


@login_required
def import_existing_route(request, route_id):
    """
    Add checkpoints, start place and end place to a route that has already been populated with `geom` and `data` (eg.
    after a GPX import).
    """
    route = get_object_or_404(Route, pk=route_id, athlete=request.user.athlete)

    if request.method == "POST":
        route_form = RouteForm(request.POST, instance=route)
        new_route = save_detail_forms(request, route_form)

        if new_route:
            messages.success(request, "Route successfully imported")
            return redirect("routes:route", pk=route_id)
    else:
        route_form = RouteForm(instance=route)

    context = {
        "object": route,
        "form": route_form,
    }

    return render(request, "routes/route_form.html", context)


@login_required
@remote_connection
def switzerland_mobility_login(request):

    template = "importers/switzerland_mobility/login.html"

    # POST request, validate and login
    if request.method == "POST":

        # instantiate login form and populate it with POST data:
        form = SwitzerlandMobilityLogin(request.POST)

        # If the form validates,
        # try to retrieve the Switzerland Mobility cookies
        if form.is_valid():
            cookies = form.retrieve_authorization_cookie(request)

            # cookies retrieved successfully
            if cookies:
                # add cookies to the user session
                request.session["switzerland_mobility_cookies"] = cookies
                # redirect to the route list
                return redirect("import_routes", data_source="switzerland_mobility")

        # something went wrong, render the login page,
        context = {"form": form}
        return render(request, template, context)

    # print the form
    elif request.method == "GET":
        context = {"form": SwitzerlandMobilityLogin()}
        return render(request, template, context)

    else:
        return HttpResponse("Method not allowed", status=405)
