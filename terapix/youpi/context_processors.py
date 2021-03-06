
"""
A set of custom Youpi request processors that return dictionaries to be merged into a
template context. Each function takes the request object as its only parameter
and returns a dictionary to add to the context.

They are referenced from the setting TEMPLATE_CONTEXT_PROCESSORS and used by
RequestContext.
"""

import django.conf

def appmenu(request):
    """
    Returns context variables for Youpi's release system (Application menu).
    """
    from django.core.urlresolvers import reverse
    app_menu = {
        'normal' : (    
            {'title' : 'Home',              'id' : 'home',          'href' : reverse('terapix.youpi.views.home')},
            {'title' : 'Ingestion',         'id' : 'ing',           'href' : reverse('terapix.youpi.cviews.ingestion.home')},
            {'title' : 'Tags',              'id' : 'tags',          'href' : reverse('terapix.youpi.cviews.tags.home')},
            {'title' : 'Processing',        'id' : 'processing',    'href' : reverse('terapix.youpi.views.processing')},
            {'title' : 'Active Monitoring', 'id' : 'monitoring',    'href' : reverse('terapix.youpi.cviews.condor.monitoring')},
            {'title' : 'Results',           'id' : 'results',       'href' : reverse('terapix.youpi.cviews.results.home')},
            {'title' : 'Reporting',         'id' : 'reporting',     'href' : reverse('terapix.youpi.cviews.reporting.reporting')},
        ),
        'apart' : [     
            # Display order is inverted
            {'title' : 'Preferences',       'id' : 'preferences',   'href' : reverse('terapix.youpi.cviews.pref.home')},
            {'title' : 'Condor Setup',      'id' : 'condorsetup',   'href' : reverse('terapix.youpi.cviews.condor.home')},
            {'title' : 'Processing Cart',   'id' : 'processingcart','href' : reverse('terapix.youpi.cviews.processingcart.home')},
        ]
    }
    if django.conf.settings.DEBUG:
        app_menu['apart'].insert(0, {'title' : 'Unit Testing', 'id' : 'unittesting', 'href' : reverse('terapix.youpi.views.main_test_runner') + '?testpage=/youpi/test/suite/'})

    return {'menu': app_menu}

def settings(request):
    """
    Returns a reference to application settings
    """
    return {'settings': django.conf.settings}

def version(request):
    """Return version information if available."""
    try:
        from terapix.youpi import __version__ as version
    except ImportError:
        version = 'unknown'

    return {'appversion': version}
