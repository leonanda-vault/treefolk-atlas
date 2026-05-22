"""
convert_points_to_trees.py — QGIS Processing Algorithm: Point-to-Tree Converter
==================================================================================

Takes any point layer from surveyors (with arbitrary column names and units)
and converts it into a standardised i-Tree SEA tree inventory layer.

Handles:
  - Field name remapping (e.g. "NAMA_POHON" → "species", "DBH_MM" → "dbh_cm")
  - Unit conversions (mm→cm, inches→cm)
  - Condition code translation (numeric 1-5 → text)
  - Common name → scientific name lookup via the species database
  - Auto-generates tree IDs if missing
  - CRS reprojection to WGS 84

Appears in the Processing Toolbox as:
  i-Tree SEA → Convert Points to Tree Inventory
"""

from __future__ import annotations

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterField,
    QgsProcessingParameterEnum,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterFile,
    QgsField,
    QgsFields,
    QgsFeature,
    QgsFeatureSink,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsProcessingException,
)
from PyQt5.QtCore import QVariant


class ConvertPointsToTreesAlgorithm(QgsProcessingAlgorithm):
    """Converts raw surveyor point data into standardised tree inventory."""

    # Parameter keys
    INPUT = "INPUT"
    SPECIES_FIELD = "SPECIES_FIELD"
    SPECIES_TYPE = "SPECIES_TYPE"
    DBH_FIELD = "DBH_FIELD"
    DBH_UNIT = "DBH_UNIT"
    HEIGHT_FIELD = "HEIGHT_FIELD"
    CONDITION_FIELD = "CONDITION_FIELD"
    CONDITION_FORMAT = "CONDITION_FORMAT"
    ID_FIELD = "ID_FIELD"
    ID_PREFIX = "ID_PREFIX"
    DATABASE = "DATABASE"
    OUTPUT = "OUTPUT"

    UNIT_CHOICES = ["cm (centimetres)", "mm (millimetres)", "in (inches)"]
    COND_CHOICES = ["Text (excellent/good/fair/poor/dead)", "Numeric (1=dead … 5=excellent)"]
    SPECIES_CHOICES = ["Scientific name", "Common name (will lookup scientific)"]

    def tr(self, string: str) -> str:
        return QCoreApplication.translate("ConvertPointsToTrees", string)

    def createInstance(self):
        return ConvertPointsToTreesAlgorithm()

    def name(self) -> str:
        return "convert_points_to_trees"

    def displayName(self) -> str:
        return self.tr("Convert Points to Tree Inventory")

    def group(self) -> str:
        return self.tr("Data Preparation")

    def groupId(self) -> str:
        return "data_prep"

    def shortHelpString(self) -> str:
        return self.tr(
            "Converts raw surveyor point data into a standardised i-Tree SEA "
            "tree inventory layer.\n\n"
            "Handles:\n"
            "• Field name remapping\n"
            "• DBH unit conversion (mm/inches → cm)\n"
            "• Condition code translation (numeric → text)\n"
            "• Common name → scientific name lookup\n"
            "• Auto-generated tree IDs\n"
            "• CRS reprojection to WGS 84"
        )

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer(
            self.INPUT, self.tr("Input point layer from surveyor"),
            [QgsProcessing.TypeVectorPoint],
        ))
        self.addParameter(QgsProcessingParameterField(
            self.SPECIES_FIELD, self.tr("Species / tree name field"),
            parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.String,
        ))
        self.addParameter(QgsProcessingParameterEnum(
            self.SPECIES_TYPE, self.tr("Species field contains"),
            options=self.SPECIES_CHOICES, defaultValue=0,
        ))
        self.addParameter(QgsProcessingParameterField(
            self.DBH_FIELD, self.tr("DBH / diameter field"),
            parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Numeric,
        ))
        self.addParameter(QgsProcessingParameterEnum(
            self.DBH_UNIT, self.tr("DBH unit in source data"),
            options=self.UNIT_CHOICES, defaultValue=0,
        ))
        self.addParameter(QgsProcessingParameterField(
            self.HEIGHT_FIELD, self.tr("Height field — optional"),
            parentLayerParameterName=self.INPUT,
            type=QgsProcessingParameterField.Numeric,
            optional=True,
        ))
        self.addParameter(QgsProcessingParameterField(
            self.CONDITION_FIELD, self.tr("Condition field — optional"),
            parentLayerParameterName=self.INPUT,
            optional=True,
        ))
        self.addParameter(QgsProcessingParameterEnum(
            self.CONDITION_FORMAT, self.tr("Condition format"),
            options=self.COND_CHOICES, defaultValue=0,
        ))
        self.addParameter(QgsProcessingParameterField(
            self.ID_FIELD, self.tr("Existing tree ID field — optional"),
            parentLayerParameterName=self.INPUT,
            optional=True,
        ))
        self.addParameter(QgsProcessingParameterString(
            self.ID_PREFIX, self.tr("Auto-ID prefix (e.g. JKT-2024)"),
            defaultValue="TREE",
        ))
        self.addParameter(QgsProcessingParameterFile(
            self.DATABASE, self.tr("Species database (.db) — optional"),
            behavior=QgsProcessingParameterFile.File,
            extension="db",
            optional=True,
        ))
        self.addParameter(QgsProcessingParameterVectorDestination(
            self.OUTPUT, self.tr("Standardised tree inventory layer"),
        ))

    def processAlgorithm(self, parameters, context, feedback):
        # ── Deferred imports ──
        try:
            from itree_sea.database import lookup_species
        except ImportError:
            raise QgsProcessingException(
                "itree_sea package not installed in QGIS Python."
            )
        from pathlib import Path

        # ── Resolve parameters ──
        source = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        species_field = self.parameterAsString(parameters, self.SPECIES_FIELD, context)
        species_type = self.parameterAsEnum(parameters, self.SPECIES_TYPE, context)
        dbh_field = self.parameterAsString(parameters, self.DBH_FIELD, context)
        dbh_unit = self.parameterAsEnum(parameters, self.DBH_UNIT, context)
        height_field = self.parameterAsString(parameters, self.HEIGHT_FIELD, context)
        cond_field = self.parameterAsString(parameters, self.CONDITION_FIELD, context)
        cond_format = self.parameterAsEnum(parameters, self.CONDITION_FORMAT, context)
        id_field = self.parameterAsString(parameters, self.ID_FIELD, context)
        id_prefix = self.parameterAsString(parameters, self.ID_PREFIX, context)
        db_file = self.parameterAsString(parameters, self.DATABASE, context)
        db_path = Path(db_file) if db_file else None

        # ── Output schema (standardised) ──
        out_fields = QgsFields()
        field_defs = [
            ("tree_id", QVariant.String),
            ("species", QVariant.String),
            ("common_name", QVariant.String),
            ("dbh_cm", QVariant.Double),
            ("height_m", QVariant.Double),
            ("condition", QVariant.String),
            ("is_palm", QVariant.Int),
            ("growth_rate", QVariant.String),
            ("match_level", QVariant.String),
            ("original_name", QVariant.String),
        ]
        for fname, ftype in field_defs:
            out_fields.append(QgsField(fname, ftype))

        # ── CRS transform to WGS 84 ──
        target_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = None
        if source.crs() != target_crs:
            transform = QgsCoordinateTransform(
                source.crs(), target_crs, QgsProject.instance()
            )

        # ── Output sink ──
        (sink, dest_id) = self.parameterAsSink(
            parameters, self.OUTPUT, context,
            out_fields, source.wkbType(), target_crs,
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        # ── Conversion maps ──
        NUMERIC_CONDITION = {5: "excellent", 4: "good", 3: "fair", 2: "poor", 1: "dead", 0: "dead"}

        # ── Process ──
        total = source.featureCount()
        for idx, feature in enumerate(source.getFeatures(), start=1):
            if feedback.isCanceled():
                break

            # --- Species ---
            raw_name = str(feature[species_field] or "").strip()
            scientific_name = ""
            common_name = ""
            is_palm = 0
            growth_rate = "moderate"
            match_level = "none"

            if species_type == 1:  # Common name → lookup
                sp = lookup_species(common_name=raw_name, db_path=db_path)
                if sp:
                    scientific_name = sp.scientific_name
                    common_name = sp.common_name
                    is_palm = 1 if sp.is_palm else 0
                    growth_rate = sp.growth_rate
                    match_level = "species"
                else:
                    scientific_name = raw_name  # fallback: use as-is
                    common_name = raw_name
                    match_level = "unmatched"
            else:  # Scientific name
                scientific_name = raw_name
                sp = lookup_species(scientific_name=raw_name, db_path=db_path)
                if sp:
                    common_name = sp.common_name
                    is_palm = 1 if sp.is_palm else 0
                    growth_rate = sp.growth_rate
                    match_level = "species"
                else:
                    match_level = "unmatched"

            # --- DBH ---
            dbh_raw = self._safe_float(feature[dbh_field], 15.0)
            if dbh_unit == 1:    # mm → cm
                dbh_cm = dbh_raw / 10.0
            elif dbh_unit == 2:  # inches → cm
                dbh_cm = dbh_raw * 2.54
            else:
                dbh_cm = dbh_raw

            # --- Height ---
            height_m = self._safe_float(feature[height_field], None) if height_field else None

            # --- Condition ---
            condition = "good"
            if cond_field:
                raw_cond = feature[cond_field]
                if cond_format == 1:  # Numeric
                    try:
                        condition = NUMERIC_CONDITION.get(int(raw_cond), "fair")
                    except (ValueError, TypeError):
                        condition = "fair"
                else:
                    condition = str(raw_cond or "good").strip().lower()
                    if condition not in ("excellent", "good", "fair", "poor", "critical", "dead"):
                        condition = "fair"

            # --- Tree ID ---
            if id_field:
                tree_id = str(feature[id_field] or "")
            else:
                tree_id = f"{id_prefix}-{idx:04d}"

            # --- Geometry (reproject if needed) ---
            geom = feature.geometry()
            if transform and not geom.isEmpty():
                geom.transform(transform)

            # --- Write output ---
            out_feat = QgsFeature(out_fields)
            out_feat.setGeometry(geom)
            out_feat.setAttributes([
                tree_id,
                scientific_name,
                common_name,
                round(dbh_cm, 1),
                round(height_m, 1) if height_m else None,
                condition,
                is_palm,
                growth_rate,
                match_level,
                raw_name,
            ])
            sink.addFeature(out_feat, QgsFeatureSink.FastInsert)
            feedback.setProgress(int(idx / total * 100))

        feedback.pushInfo(f"Converted {total} surveyor points → standardised tree inventory")
        return {self.OUTPUT: dest_id}

    @staticmethod
    def _safe_float(value, default):
        if value is None:
            return default
        try:
            v = float(value)
            return v if v == v else default
        except (ValueError, TypeError):
            return default
