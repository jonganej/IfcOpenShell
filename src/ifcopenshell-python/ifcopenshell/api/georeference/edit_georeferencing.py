# IfcOpenShell - IFC toolkit and geometry engine
# Copyright (C) 2021 Dion Moult <dion@thinkmoult.com>
#
# This file is part of IfcOpenShell.
#
# IfcOpenShell is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# IfcOpenShell is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with IfcOpenShell.  If not, see <http://www.gnu.org/licenses/>.

import ifcopenshell
from typing import Optional, Any


def edit_georeferencing(
    file: ifcopenshell.file,
    coordinate_operation: Optional[dict[str, Any]] = None,
    projected_crs: Optional[dict[str, Any]] = None,
    true_north: Optional[tuple[float, float]] = None,
) -> None:
    """Edits the attributes of a map conversion, projected CRS, and true north

    Setting the correct georeferencing parameters is a complex topic and
    should ideally be done with three parties present: the lead architect,
    surveyor, and a third-party digital engineer with expertise in IFC to
    moderate. For more information, read the BlenderBIM Add-on documentation
    for Georeferencing:
    https://docs.blenderbim.org/users/georeferencing.html

    For more information about the attributes and data types of an
    IfcMapConversion, consult the IFC documentation.

    For more information about the attributes and data types of an
    IfcProjectedCRS, consult the IFC documentation.

    True north is defined as a unitised 2D vector pointing to true north.
    Note that true north is not part of georeferencing, and is only
    optionally provided as a reference value, typically for solar analysis.

    See ifcopenshell.util.geolocation for more utilities to convert to and
    from local and map coordinates to check your results.

    :param coordinate_operation: The dictionary of attribute names and values
        you want to edit.
    :type coordinate_operation: dict, optional
    :param projected_crs: The IfcProjectedCRS dictionary of attribute
        names and values you want to edit.
    :type projected_crs: dict, optional
    :param true_north: A unitised 2D vector, where each ordinate is a float
    :type true_north: tuple[float, float], optional
    :return: None
    :rtype: None

    Example:

    .. code:: python

        ifcopenshell.api.run("georeference.add_georeferencing", model)
        # This is the simplest scenario, a defined CRS (GDA2020 / MGA Zone
        # 56, typically used in Sydney, Australia) but with no local
        # coordinates. This is only recommended for horizontal construction
        # projects, not for vertical construction (such as buildings).
        ifcopenshell.api.run("georeference.edit_georeferencing", model,
            projected_crs={"Name": "EPSG:7856"})

        # For buildings, it is almost always recommended to specify map
        # conversion parameters to a false origin and orientation to project
        # north. See the diagram in the BlenderBIM Add-on Georeferencing
        # documentation for correct calculation of the X Axis Abcissa and
        # Ordinate.
        ifcopenshell.api.run("georeference.edit_georeferencing", model,
            projected_crs={"Name": "EPSG:7856"},
            coordinate_operation={
                "Eastings": 335087.17, # The architect nominates a false origin
                "Northings": 6251635.41, # The architect nominates a false origin
                # Note: this is the angle difference between Project North
                # and Grid North. Remember: True North should never be used!
                "XAxisAbscissa": cos(radians(-30)), # The architect nominates a project north
                "XAxisOrdinate": sin(radians(-30)), # The architect nominates a project north
                "Scale": 0.99956, # Ask your surveyor for your site's average combined scale factor!
            })
    """
    usecase = Usecase()
    usecase.file = file
    usecase.settings = {
        "coordinate_operation": coordinate_operation or {},
        "projected_crs": projected_crs or {},
        "true_north": true_north or [],
    }
    return usecase.execute()


class Usecase:
    def execute(self):
        self.set_true_north()
        if self.file.schema == "IFC2X3":
            if not (project := self.file.by_type("IfcProject")):
                return
            project = project[0]
            if (crs := ifcopenshell.util.element.get_pset(project, "ePSet_ProjectedCRS")):
                crs = self.file.by_id(crs["id"])
                for k, v in self.settings["projected_crs"].items():
                    if k == "Description":
                        v = self.file.createIfcText(v)
                    elif k == "Name":
                        v = self.file.createIfcLabel(v)
                    else:
                        v = self.file.createIfcIdentifier(v)
                ifcopenshell.api.pset.edit_pset(self.file, crs, properties=self.settings["projected_crs"])
            if (conversion := ifcopenshell.util.element.get_pset(project, "ePSet_MapConversion")):
                conversion = self.file.by_id(conversion["id"])
                for k, v in self.settings["coordinate_operation"].items():
                    if k in ("XAxisAbscissa", "XAxisOrdinate", "Scale"):
                        v = self.file.createIfcReal(v)
                    else:
                        v = self.file.createIfcLengthMeasure(v)
                ifcopenshell.api.pset.edit_pset(self.file, conversion, properties=self.settings["coordinate_operation"])
            return
        coordinate_operation = self.file.by_type("IfcCoordinateOperation")[0]
        projected_crs = self.file.by_type("IfcProjectedCRS")[0]
        for name, value in self.settings["coordinate_operation"].items():
            setattr(coordinate_operation, name, value)
        for name, value in self.settings["projected_crs"].items():
            setattr(projected_crs, name, value)

    def set_true_north(self):
        if not self.settings["true_north"]:
            return
        for context in self.file.by_type("IfcGeometricRepresentationContext", include_subtypes=False):
            if context.TrueNorth:
                if len(self.file.get_inverse(context.TrueNorth)) != 1:
                    context.TrueNorth = self.file.create_entity("IfcDirection")
            else:
                context.TrueNorth = self.file.create_entity("IfcDirection")
            direction = context.TrueNorth
            if self.settings["true_north"] is None:
                # TODO: code will never be executed since None value
                # is substituted by an empty list
                context.TrueNorth = self.settings["true_north"]
            elif context.CoordinateSpaceDimension == 2:
                direction.DirectionRatios = self.settings["true_north"][0:2]
            else:
                direction.DirectionRatios = self.settings["true_north"][0:2] + [0.0]
