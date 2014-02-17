# -*- coding: utf-8 -*-


# OpenFisca -- A versatile microsimulation software
# By: OpenFisca Team <contact@openfisca.fr>
#
# Copyright (C) 2011, 2012, 2013, 2014 OpenFisca Team
# https://github.com/openfisca
#
# This file is part of OpenFisca.
#
# OpenFisca is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# OpenFisca is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""Decorators to wrap functions to make them WSGI applications.

The main decorator :class:`wsgify` turns a function into a WSGI application.
"""


import collections
import json

import webob.dec
import webob.exc


N_ = lambda message: message


errors_title = {
    400: N_("Unable to Access"),
    401: N_("Access Denied"),
    403: N_("Access Denied"),
    404: N_("Unable to Access"),
    }


wsgify = webob.dec.wsgify


def discard_empty_items(data):
    if isinstance(data, collections.Mapping):
        # Use type(data) to keep OrderedDicts.
        data = type(data)(
            (name, discard_empty_items(value))
            for name, value in data.iteritems()
            if value is not None
            )
    return data


def handle_cross_origin_resource_sharing(ctx):
    # Cf http://www.w3.org/TR/cors/#resource-processing-model
    environ = ctx.req.environ
    headers = []
    origin = environ.get('HTTP_ORIGIN')
    if origin is None:
        return headers
    if ctx.req.method == 'OPTIONS':
        method = environ.get('HTTP_ACCESS_CONTROL_REQUEST_METHOD')
        if method is None:
            return headers
        headers_name = environ.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS') or ''
        headers.append(('Access-Control-Allow-Credentials', 'true'))
        headers.append(('Access-Control-Allow-Origin', origin))
        headers.append(('Access-Control-Max-Age', '3628800'))
        headers.append(('Access-Control-Allow-Methods', method))
        headers.append(('Access-Control-Allow-Headers', headers_name))
        raise webob.exc.status_map[204](headers = headers)  # No Content
    headers.append(('Access-Control-Allow-Credentials', 'true'))
    headers.append(('Access-Control-Allow-Origin', origin))
    headers.append(('Access-Control-Expose-Headers', 'WWW-Authenticate'))
    return headers


def respond_json(ctx, data, code = None, headers = None, jsonp = None):
    """Return a JSON response.

    This function is optimized for JSON following
    `Google JSON Style Guide <http://google-styleguide.googlecode.com/svn/trunk/jsoncstyleguide.xml>`_, but will handle
    any JSON except for HTTP errors.
    """
    if isinstance(data, collections.Mapping):
        # Remove null properties as recommended by Google JSON Style Guide.
        data = discard_empty_items(data)
        error = data.get('error')
    else:
        error = None
    if headers is None:
        headers = []
    if jsonp:
        content_type = 'application/javascript; charset=utf-8'
    else:
        content_type = 'application/json; charset=utf-8'
    if error:
        code = code or error['code']
        assert isinstance(code, int)
        response = webob.exc.status_map[code](headers = headers)
        response.content_type = content_type
        if code == 204:  # No content
            return response
        if error.get('code') is None:
            error['code'] = code
        if error.get('message') is None:
            title = errors_title.get(code)
            title = ctx._(title) if title is not None else response.status
            error['message'] = title
    else:
        response = ctx.req.response
        response.content_type = content_type
        if code is not None:
            response.status = code
        response.headers.update(headers)
#    text = unicode(json.dumps(data, encoding = 'utf-8', ensure_ascii = False))
    text = unicode(json.dumps(data, encoding = 'utf-8', ensure_ascii = False, indent = 2))
    if jsonp:
        text = u'{0}({1})'.format(jsonp, text)
    response.text = text
    return response
