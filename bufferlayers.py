# -*- coding: utf-8 -*-

"""
***************************************************************************
    bufferlayers.py
    ---------------------
    Date                 : August 2019
    Copyright            : (C) 2019 by Giovanni Manghi
    Email                : giovanni dot manghi at naturalgis dot pt
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Alexander Bruy and Giovanni Manghi'
__date__ = 'August 2019'
__copyright__ = '(C) 2019, Giovanni Manghi'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os

from qgis.PyQt.QtGui import QIcon

from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterField,
                       QgsProcessingParameterString,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterDistance,
                       QgsProcessingParameterVectorLayer,
                       QgsDataSourceUri
                      )
from processing.algs.gdal.GdalUtils import GdalUtils

pluginPath = os.path.dirname(__file__)


class bufferlayers(QgsProcessingAlgorithm):

    INPUT_LAYER = 'INPUT_LAYER'
    FIELDS = 'FIELDS'
    DISTANCE = 'DISTANCE'
    DISSOLVEALL = 'DISSOLVEALL'
    DISSFIELD = 'DISSFIELD'
    SINGLE = 'SINGLE'
    TABLE = 'TABLE'
    SCHEMA = 'SCHEMA'
    OPTIONS = 'OPTIONS'

    def __init__(self):
        super().__init__()

    def createInstance(self):
        return type(self)()

    def icon(self):
        return QIcon(os.path.join(pluginPath, 'icons', 'postgis.png'))

    def name(self):
        return 'bufferfixeddistance'

    def displayName(self):
        return 'Buffer (fixed distance)'

    def group(self):
        return 'Vector geoprocessing'

    def groupId(self):
        return 'vectorgeoprocessing'

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer(self.INPUT_LAYER,
                                                            'Input layer',
                                                            [QgsProcessing.TypeVectorAnyGeometry]))
        self.addParameter(QgsProcessingParameterField(self.FIELDS,
                                                      'Attributes to keep',
                                                      None,
                                                      self.INPUT_LAYER,
                                                      allowMultiple=True))
        self.addParameter(QgsProcessingParameterDistance(self.DISTANCE,
                                                         'Buffer distance',
                                                         0.0001,
                                                         self.INPUT_LAYER,
                                                         False,
                                                         0,
                                                         1000000000.0))
        self.addParameter(QgsProcessingParameterBoolean(self.DISSOLVEALL,
                                                        'Dissolve all',
                                                        False))
        self.addParameter(QgsProcessingParameterField(self.DISSFIELD,
                                                      'Dissolve by attribute (ignored if "Dissolve all" is selected)',
                                                      None,
                                                      self.INPUT_LAYER))
        self.addParameter(QgsProcessingParameterBoolean(self.SINGLE,
                                                        'Force output as singlepart',
                                                        False))
        self.addParameter(QgsProcessingParameterString(self.SCHEMA,
                                                       'Output schema',
                                                       'public'))
        self.addParameter(QgsProcessingParameterString(self.TABLE,
                                                       'Output table name',
                                                       'buffer'))
        self.addParameter(QgsProcessingParameterString(self.OPTIONS,
                                                       'Additional creation options (see ogr2ogr manual)',
                                                       '',
                                                       optional=True))

    def processAlgorithm(self, parameters, context, feedback):
        inLayer = self.parameterAsVectorLayer(parameters, self.INPUT_LAYER, context)
        ogrLayer = GdalUtils.ogrConnectionStringFromLayer(inLayer)
        layername = GdalUtils.ogrLayerName(inLayer.dataProvider().dataSourceUri())

        dsUri = QgsDataSourceUri(inLayer.source())
        geomColumn = dsUri.geometryColumn()
        srid = inLayer.crs().postgisSrid()

        fields = self.parameterAsFields(parameters, self.FIELDS, context)
        dissfield = self.parameterAsString(parameters, self.DISSFIELD, context)

        schema = self.parameterAsString(parameters, self.SCHEMA, context)
        table = self.parameterAsString(parameters, self.TABLE, context)
        options = self.parameterAsString(parameters, self.OPTIONS, context)

        distance = str(self.parameterAsDouble(parameters, self.DISTANCE, context))
        dissolveall = self.parameterAsBool(parameters, self.DISSOLVEALL, context)
        single = self.parameterAsBool(parameters, self.SINGLE, context)

        if len(fields) > 0:
           fieldstring = ",".join(fields) + ","
        else:
           fieldstring = ""

        if dissolveall:
             if single:
                query = '-sql "SELECT (ST_Dump(ST_Multi(ST_Union(ST_Buffer(' + geomColumn + ',' + distance + '))))).geom::geometry(POLYGON,' + str(srid) + ') AS geom FROM ' + layername + '" -nln ' + schema + '.' + table + ' -nlt POLYGON -lco FID=gid -lco GEOMETRY_NAME=geom --config PG_USE_COPY YES'
             else:
                query = '-sql "SELECT (ST_Multi(ST_Union(ST_Buffer(' + geomColumn + ',' + distance + '))))::geometry(MULTIPOLYGON,' + str(srid) + ') AS geom FROM ' + layername + '" -nln ' + schema + '.' + table + ' -nlt MULTIPOLYGON -lco FID=gid -lco GEOMETRY_NAME=geom --config PG_USE_COPY YES'
        else:
           if dissfield is None:
             if single:
                query = '-sql "SELECT ' + dissfield + ',(ST_Dump(ST_Union(ST_Buffer(' + geomColumn + ',' + distance + ')))).geom::geometry(POLYGON,' + str(srid) + ') AS geom FROM ' + layername + ' GROUP BY ' + dissfield + '" -nln ' + schema + '.' + table + ' -nlt POLYGON -lco FID=gid -lco GEOMETRY_NAME=geom --config PG_USE_COPY YES'
             else:
                query = '-sql "SELECT ' + dissfield + ',(ST_Multi(ST_Union(ST_Buffer(' + geomColumn + ',' + distance + '))))::geometry(MULTIPOLYGON,' + str(srid) + ') AS geom FROM ' + layername + ' GROUP BY ' + dissfield + '" -nln ' + schema + '.' + table + ' -nlt MULTIPOLYGON -lco FID=gid -lco GEOMETRY_NAME=geom --config PG_USE_COPY YES'
           else:
             if single:
                query = '-sql "SELECT ' + fieldstring + '(ST_Dump(ST_Multi(ST_Buffer(' + geomColumn + ',' + distance + ')))).geom::geometry(POLYGON,' + str(srid) + ') AS geom FROM ' + layername + '" -nln ' + schema + '.' + table + ' -nlt POLYGON -lco FID=gid -lco GEOMETRY_NAME=geom --config PG_USE_COPY YES'
             else:
                query = '-sql "SELECT ' + fieldstring + '(ST_Multi(ST_Buffer(' + geomColumn + ',' + distance + ')))::geometry(MULTIPOLYGON,' + str(srid) + ') AS geom FROM ' + layername + '" -nln ' + schema + '.' + table + ' -nlt MULTIPOLYGON -lco FID=gid -lco GEOMETRY_NAME=geom --config PG_USE_COPY YES'

        arguments = []
        arguments.append('-f')
        arguments.append('PostgreSQL')
        arguments.append(ogrLayer)
        arguments.append(ogrLayer)
        arguments.append(query)
        arguments.append('-overwrite')

        if len(options) > 0:
            arguments.append(options)

        commands = ['ogr2ogr', GdalUtils.escapeAndJoin(arguments)]
        GdalUtils.runGdal(commands, feedback)

        return {}
