"""
enrich_tree_layer.py — QGIS Processing Algorithm: Enrich Tree Inventory
=========================================================================

Takes a point vector layer of surveyed trees, runs i-Tree SEA
calculations on each feature, and outputs a new layer with
ecosystem benefit columns appended.

Appears in the Processing Toolbox as:
  i-Tree SEA → Enrich Tree Inventory Layer

Input requirements:
  The input layer must have a 'species' field (scientific name)
  and a 'dbh_cm' field.  Optional: 'height_m', 'condition'.
"""

from __future__ import annotations

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterField,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterFile,
    QgsField,
    QgsFields,
    QgsFeature,
    QgsFeatureSink,
    QgsWkbTypes,
    QgsProcessingException,
)
from PyQt5.QtCore import QVariant


class EnrichTreeLayerAlgorithm(QgsProcessingAlgorithm):
    """Processing algorithm that enriches a tree inventory vector layer."""

    # Parameter keys
    INPUT = "INPUT"
    SPECIES_FIELD = "SPECIES_FIELD"
    DBH_FIELD = "DBH_FIELD"
    HEIGHT_FIELD = "HEIGHT_FIELD"
    CONDITION_FIELD = "CONDITION_FIELD"
    LAI = "LAI"
    DATABASE = "DATABASE"
    OUTPUT = "OUTPUT"

    def tr(self, string: str) -> str:
        return QCoreApplication.translate("EnrichTreeLayer", string)

    def createInstance(self):
        return EnrichTreeLayerAlgorithm()

    def name(self) -> str:
        return "enrich_tree_inventory"

    def displayName(self) -> str:
        return self.tr("Enrich Tree Inventory Layer")

    def group(self) -> str:
        return self.tr("Analysis")

    def groupId(self) -> str:
        return "analysis"

    def shortHelpString(self) -> str:
        return self.tr(
            "Calculates biomass, carbon storage, annual carbon sequestration, "
            "stormwater interception, and air pollution removal for each tree "
            "in the input layer.\n\n"
            "Required fields: species (scientific name), dbh_cm.\n"
            "Optional fields: height_m, condition.\n\n"
            "Uses Chave et al. (2014) pantropical allometric models with "
            "species/genus-level wood density from the i-Tree SEA database."
        )

    def initAlgorithm(self, config=None):
        """Define the algorithm's input and output parameters."""

        # Input vector layer (point geometry)
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT,
                self.tr("Input tree inventory layer"),
                [QgsProcessing.TypeVectorPoint],
            )
        )

        # Species field mapping
        self.addParameter(
            QgsProcessingParameterField(
                self.SPECIES_FIELD,
                self.tr("Species field (scientific name)"),
                defaultValue="species",
                parentLayerParameterName=self.INPUT,
                type=QgsProcessingParameterField.String,
            )
        )

        # DBH field mapping
        self.addParameter(
            QgsProcessingParameterField(
                self.DBH_FIELD,
                self.tr("DBH field (cm)"),
                defaultValue="dbh_cm",
                parentLayerParameterName=self.INPUT,
                type=QgsProcessingParameterField.Numeric,
            )
        )

        # Height field (optional)
        self.addParameter(
            QgsProcessingParameterField(
                self.HEIGHT_FIELD,
                self.tr("Height field (m) — optional"),
                defaultValue="height_m",
                parentLayerParameterName=self.INPUT,
                type=QgsProcessingParameterField.Numeric,
                optional=True,
            )
        )

        # Condition field (optional)
        self.addParameter(
            QgsProcessingParameterField(
                self.CONDITION_FIELD,
                self.tr("Condition field — optional"),
                defaultValue="condition",
                parentLayerParameterName=self.INPUT,
                type=QgsProcessingParameterField.String,
                optional=True,
            )
        )

        # LAI parameter
        self.addParameter(
            QgsProcessingParameterNumber(
                self.LAI,
                self.tr("Leaf Area Index (LAI)"),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=5.0,
                minValue=1.0,
                maxValue=12.0,
            )
        )

        # Database file (optional — uses default if not specified)
        self.addParameter(
            QgsProcessingParameterFile(
                self.DATABASE,
                self.tr("Species database (.db) — optional"),
                behavior=QgsProcessingParameterFile.File,
                extension="db",
                optional=True,
            )
        )

        # Output layer
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT,
                self.tr("Enriched tree layer"),
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """Run the enrichment calculation on every feature."""

        # ── Import i-Tree SEA core (deferred to avoid import errors at plugin load) ──
        try:
            from itree_sea.database import get_coefficients, lookup_species
            from itree_sea.engine import (
                calculate_biomass,
                calculate_sequestration,
                estimate_stormwater_interception,
                estimate_pollution_removal,
            )
        except ImportError:
            raise QgsProcessingException(
                "The 'itree_sea' package is not installed in QGIS's Python environment.\n"
                "Install it by running in the QGIS Python console:\n"
                "  import subprocess; subprocess.check_call(['python', '-m', 'pip', 'install', '-e', '/path/to/itree-sea[gis]'])"
            )

        from pathlib import Path

        # ── Resolve parameters ──
        source = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        species_field = self.parameterAsString(parameters, self.SPECIES_FIELD, context)
        dbh_field = self.parameterAsString(parameters, self.DBH_FIELD, context)
        height_field = self.parameterAsString(parameters, self.HEIGHT_FIELD, context)
        condition_field = self.parameterAsString(parameters, self.CONDITION_FIELD, context)
        lai = self.parameterAsDouble(parameters, self.LAI, context)
        db_file = self.parameterAsString(parameters, self.DATABASE, context)
        db_path = Path(db_file) if db_file else None

        # ── Build output fields (input fields + new benefit columns) ──
        out_fields = QgsFields(source.fields())

        new_field_names = [
            ("agb_kg", QVariant.Double),
            ("bgb_kg", QVariant.Double),
            ("total_bio_kg", QVariant.Double),
            ("carbon_kg", QVariant.Double),
            ("seq_kg_yr", QVariant.Double),
            ("storm_l", QVariant.Double),
            ("pm25_g", QVariant.Double),
            ("no2_g", QVariant.Double),
            ("o3_g", QVariant.Double),
            ("so2_g", QVariant.Double),
            ("poll_tot_g", QVariant.Double),
            ("match_lvl", QVariant.String),
            ("eq_used", QVariant.String),
        ]

        for fname, ftype in new_field_names:
            out_fields.append(QgsField(fname, ftype))

        # ── Create output sink ──
        (sink, dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            out_fields,
            source.wkbType(),
            source.sourceCrs(),
        )

        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        # ── Process features ──
        total = source.featureCount()
        features = source.getFeatures()

        for current, feature in enumerate(features):
            if feedback.isCanceled():
                break

            # Read input attributes
            species_name = str(feature[species_field] or "").strip()
            dbh = self._safe_float(feature[dbh_field], 15.0)
            height = self._safe_float(feature[height_field], None) if height_field else None
            condition = str(feature[condition_field] or "good").strip() if condition_field else "good"

            # Resolve coefficients
            sp_record = lookup_species(scientific_name=species_name, db_path=db_path)
            is_palm = sp_record.is_palm if sp_record else False
            growth_rate = sp_record.growth_rate if sp_record else "moderate"
            genus = species_name.split()[0] if species_name else None

            coeffs = get_coefficients(
                scientific_name=species_name if species_name else None,
                genus=genus,
                db_path=db_path,
            )

            # Calculate
            bio = calculate_biomass(dbh, height, coeffs, condition=condition, is_palm=is_palm)
            seq = calculate_sequestration(dbh, height, coeffs, growth_rate=growth_rate, is_palm=is_palm)
            storm = estimate_stormwater_interception(dbh, lai)
            poll = estimate_pollution_removal(dbh, lai)

            # Build output feature
            out_feat = QgsFeature(out_fields)
            out_feat.setGeometry(feature.geometry())

            # Copy original attributes
            for i in range(source.fields().count()):
                out_feat.setAttribute(i, feature[i])

            # Append benefit columns
            offset = source.fields().count()
            out_feat.setAttribute(offset + 0, bio.agb_kg)
            out_feat.setAttribute(offset + 1, bio.bgb_kg)
            out_feat.setAttribute(offset + 2, bio.total_biomass_kg)
            out_feat.setAttribute(offset + 3, bio.carbon_storage_kg)
            out_feat.setAttribute(offset + 4, seq.annual_sequestration_kg)
            out_feat.setAttribute(offset + 5, storm)
            out_feat.setAttribute(offset + 6, poll.pm25_g)
            out_feat.setAttribute(offset + 7, poll.no2_g)
            out_feat.setAttribute(offset + 8, poll.o3_g)
            out_feat.setAttribute(offset + 9, poll.so2_g)
            out_feat.setAttribute(offset + 10, poll.total_g)
            out_feat.setAttribute(offset + 11, bio.match_level)
            out_feat.setAttribute(offset + 12, bio.equation_used)

            sink.addFeature(out_feat, QgsFeatureSink.FastInsert)

            feedback.setProgress(int((current + 1) / total * 100))

        return {self.OUTPUT: dest_id}

    @staticmethod
    def _safe_float(value, default):
        """Convert to float or return default."""
        if value is None:
            return default
        try:
            v = float(value)
            return v if v == v else default  # NaN check
        except (ValueError, TypeError):
            return default
