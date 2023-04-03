/********************************************************************************
 *                                                                              *
 * This file is part of IfcOpenShell.                                           *
 *                                                                              *
 * IfcOpenShell is free software: you can redistribute it and/or modify         *
 * it under the terms of the Lesser GNU General Public License as published by  *
 * the Free Software Foundation, either version 3.0 of the License, or          *
 * (at your option) any later version.                                          *
 *                                                                              *
 * IfcOpenShell is distributed in the hope that it will be useful,              *
 * but WITHOUT ANY WARRANTY; without even the implied warranty of               *
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the                 *
 * Lesser GNU General Public License for more details.                          *
 *                                                                              *
 * You should have received a copy of the Lesser GNU General Public License     *
 * along with this program. If not, see <http://www.gnu.org/licenses/>.         *
 *                                                                              *
 ********************************************************************************/

#include "mapping.h"
#define mapping POSTFIX_SCHEMA(mapping)
using namespace ifcopenshell::geometry;

#ifdef SCHEMA_HAS_IfcIndexedPolyCurve

taxonomy::item* mapping::map_impl(const IfcSchema::IfcIndexedPolyCurve* inst) {
	
	IfcSchema::IfcCartesianPointList* point_list = inst->Points();
	std::vector< std::vector<double> > coordinates;
	if (point_list->as<IfcSchema::IfcCartesianPointList2D>()) {
		coordinates = point_list->as<IfcSchema::IfcCartesianPointList2D>()->CoordList();
	} else if (point_list->as<IfcSchema::IfcCartesianPointList3D>()) {
		coordinates = point_list->as<IfcSchema::IfcCartesianPointList3D>()->CoordList();
	}

	std::vector<taxonomy::point3> points;
	points.reserve(coordinates.size());
	for (auto& coords : coordinates) {
		points.push_back(taxonomy::point3(
			coords.size() < 1 ? 0. : coords[0] * length_unit_,
			coords.size() < 2 ? 0. : coords[1] * length_unit_,
			coords.size() < 3 ? 0. : coords[2] * length_unit_));
	}

	int max_index = (int) points.size();

	auto loop = new taxonomy::loop;

	if(inst->Segments()) {
		aggregate_of_instance::ptr segments = *inst->Segments();
		for (aggregate_of_instance::it it = segments->begin(); it != segments->end(); ++it) {
			IfcUtil::IfcBaseClass* segment = *it;
			if (segment->declaration().is(IfcSchema::IfcLineIndex::Class())) {
				IfcSchema::IfcLineIndex* line = (IfcSchema::IfcLineIndex*) segment;
				std::vector<int> indices = *line;
				taxonomy::point3 previous;
				for (std::vector<int>::const_iterator jt = indices.begin(); jt != indices.end(); ++jt) {
					if (*jt < 1 || *jt > max_index) {
						throw IfcParse::IfcException("IfcIndexedPolyCurve index out of bounds for index " + boost::lexical_cast<std::string>(*jt));
					}
					const taxonomy::point3& current = points[*jt - 1];
					if (jt != indices.begin()) {
						loop->children.push_back(new taxonomy::edge(previous, current));
					}
					previous = current;
				}
			} else if (segment->declaration().is(IfcSchema::IfcArcIndex::Class())) {
				IfcSchema::IfcArcIndex* arc = (IfcSchema::IfcArcIndex*) segment;
				std::vector<int> indices = *arc;
				if (indices.size() != 3) {
					throw IfcParse::IfcException("Invalid IfcArcIndex encountered");
				}
				for (int i = 0; i < 3; ++i) {
					const int& idx = indices[i];
					if (idx < 1 || idx > max_index) {
						throw IfcParse::IfcException("IfcIndexedPolyCurve index out of bounds for index " + boost::lexical_cast<std::string>(idx));
					}
				}
				const auto& a = points[indices[0] - 1];
				const auto& b = points[indices[1] - 1];
				const auto& c = points[indices[2] - 1];

				auto circ = taxonomy::circle::from_3_points(a.ccomponents(), b.ccomponents(), c.ccomponents());
				if (circ) {
					auto e = new taxonomy::edge(a, c);
					e->basis = circ;
					loop->children.push_back(e);
				} else {
					Logger::Warning("Ignoring segment on", inst);
				}
			} else {
				throw IfcParse::IfcException("Unexpected IfcIndexedPolyCurve segment of type " + segment->declaration().name());
			}
		}
	} else if (points.begin() < points.end()) {
        auto previous = points.begin();
        for (auto current = previous+1; current < points.end(); ++current){
			loop->children.push_back(new taxonomy::edge(*previous, *current));
			previous = current;
        }
    }
	
	return loop;
}

#endif
