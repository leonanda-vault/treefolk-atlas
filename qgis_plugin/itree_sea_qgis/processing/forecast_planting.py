"""
forecast_planting.py — QGIS Processing Algorithm: Forecast Planting Benefits
==============================================================================

Takes a point vector layer of *proposed* trees (from a planting plan),
runs a multi-year growth forecast on each, and outputs a CSV table
with year-by-year ecosystem benefit projections.

Appears in the Processing Toolbox as:
  i-Tree SEA → Forecast Planting Benefits

This is the QGIS equivalent of the CAD Bridge pipeline — it lets
QGIS users who receive planting plans as Shapefiles/GeoJSON (rather
than DXF) generate benefit schedules without leaving QGIS.
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
    QgsProcessingParameterFile,
    QgsProcessingException,
)


class ForecastPlantingAlgorithm(QgsProcessingAlgorithm):
    """Processing algorithm for multi-year planting benefit forecasts."""

    INPUT = "INPUT"
    SPECIES_FIELD = "SPECIES_FIELD"
    DBH_FIELD = "DBH_FIELD"
    YEARS = "YEARS"
    LAI = "LAI"
    DATABASE = "DATABASE"
    OUTPUT_SCHEDULE = "OUTPUT_SCHEDULE"
    OUTPUT_SUMMARY = "OUTPUT_SUMMARY"

    def tr(self, string: str) -> str:
        return QCoreApplication.translate("ForecastPlanting", string)

    def createInstance(self):
        return ForecastPlantingAlgorithm()

    def name(self) -> str:
        return "forecast_planting_benefits"

    def displayName(self) -> str:
        return self.tr("Forecast Planting Benefits")

    def group(self) -> str:
        return self.tr("Analysis")

    def groupId(self) -> str:
        return "analysis"

    def shortHelpString(self) -> str:
        return self.tr(
            "Projects tree growth and ecosystem benefits over a multi-year "
            "horizon for proposed planting plans.\n\n"
            "Outputs two CSV files:\n"
            "  • Schedule: year-by-year per-tree projections\n"
            "  • Summary: final-year totals with cumulative sequestration\n\n"
            "Input layer must have: species (scientific name), dbh_cm "
            "(planting caliper, typically 5 cm for nursery stock)."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT,
                self.tr("Input planting plan layer"),
                [QgsProcessing.TypeVectorPoint],
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.SPECIES_FIELD,
                self.tr("Species field (scientific name)"),
                defaultValue="species",
                parentLayerParameterName=self.INPUT,
                type=QgsProcessingParameterField.String,
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.DBH_FIELD,
                self.tr("Initial DBH / caliper field (cm)"),
                defaultValue="dbh_cm",
                parentLayerParameterName=self.INPUT,
                type=QgsProcessingParameterField.Numeric,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.YEARS,
                self.tr("Forecast horizon (years)"),
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=25,
                minValue=1,
                maxValue=100,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.LAI,
                self.tr("Leaf Area Index"),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=5.0,
                minValue=1.0,
                maxValue=12.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                self.DATABASE,
                self.tr("Species database (.db) — optional"),
                behavior=QgsProcessingParameterFile.File,
                extension="db",
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_SCHEDULE,
                self.tr("Output schedule CSV"),
                fileFilter="CSV files (*.csv)",
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_SUMMARY,
                self.tr("Output summary CSV"),
                fileFilter="CSV files (*.csv)",
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """Run the forecast on all planting features."""

        try:
            from itree_sea.database import get_coefficients, lookup_species
            from itree_sea.engine import forecast_growth
        except ImportError:
            raise QgsProcessingException(
                "The 'itree_sea' package is not installed in QGIS's Python. "
                "Install it with: pip install -e /path/to/itree-sea"
            )

        import csv
        from pathlib import Path

        # ── Resolve parameters ──
        source = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        species_field = self.parameterAsString(parameters, self.SPECIES_FIELD, context)
        dbh_field = self.parameterAsString(parameters, self.DBH_FIELD, context)
        years = self.parameterAsInt(parameters, self.YEARS, context)
        lai = self.parameterAsDouble(parameters, self.LAI, context)
        db_file = self.parameterAsString(parameters, self.DATABASE, context)
        db_path = Path(db_file) if db_file else None
        schedule_path = self.parameterAsString(parameters, self.OUTPUT_SCHEDULE, context)
        summary_path = self.parameterAsString(parameters, self.OUTPUT_SUMMARY, context)

        # ── CSV headers ──
        schedule_headers = [
            "tree_id", "species", "year", "dbh_cm", "height_m",
            "carbon_storage_kg", "carbon_seq_kg", "stormwater_l",
            "pm25_g", "no2_g", "o3_g", "so2_g", "match_level",
        ]
        summary_headers = [
            "tree_id", "species", "final_dbh_cm", "final_height_m",
            "final_carbon_kg", "cumulative_seq_kg",
            "final_stormwater_l", "match_level",
        ]

        # ── Process ──
        total = source.featureCount()
        features = source.getFeatures()

        schedule_rows = []
        summary_rows = []

        for tree_id, feature in enumerate(features, start=1):
            if feedback.isCanceled():
                break

            species_name = str(feature[species_field] or "").strip()
            dbh = 5.0  # default planting caliper
            if dbh_field:
                try:
                    dbh = float(feature[dbh_field] or 5.0)
                except (ValueError, TypeError):
                    dbh = 5.0

            # Resolve
            sp_record = lookup_species(scientific_name=species_name, db_path=db_path)
            is_palm = sp_record.is_palm if sp_record else False
            growth_rate = sp_record.growth_rate if sp_record else "moderate"
            genus = species_name.split()[0] if species_name else None

            coeffs = get_coefficients(
                scientific_name=species_name if species_name else None,
                genus=genus,
                db_path=db_path,
            )

            # Forecast
            rows = forecast_growth(
                initial_dbh_cm=dbh,
                coefficients=coeffs,
                growth_rate=growth_rate,
                years=years,
                is_palm=is_palm,
                lai=lai,
            )

            cumulative_seq = 0.0
            for r in rows:
                cumulative_seq += r.carbon_sequestration_kg
                schedule_rows.append([
                    tree_id, species_name, r.year, r.dbh_cm, r.height_m,
                    r.carbon_storage_kg, r.carbon_sequestration_kg,
                    r.stormwater_litres, r.pm25_removed_g, r.no2_removed_g,
                    r.o3_removed_g, r.so2_removed_g, coeffs.match_level,
                ])

            final = rows[-1]
            summary_rows.append([
                tree_id, species_name, final.dbh_cm, final.height_m,
                final.carbon_storage_kg, round(cumulative_seq, 3),
                final.stormwater_litres, coeffs.match_level,
            ])

            feedback.setProgress(int(tree_id / total * 100))

        # ── Write CSVs ──
        with open(schedule_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(schedule_headers)
            writer.writerows(schedule_rows)

        with open(summary_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(summary_headers)
            writer.writerows(summary_rows)

        feedback.pushInfo(
            f"Done: {len(summary_rows)} trees × {years} years → {schedule_path}"
        )

        return {
            self.OUTPUT_SCHEDULE: schedule_path,
            self.OUTPUT_SUMMARY: summary_path,
        }
