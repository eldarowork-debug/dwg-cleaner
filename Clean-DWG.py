#!/usr/bin/env python3
"""
DWG Spline Simplifier - IMPROVED
Uses ODA File Converter + ezdxf to process drawings
"""

import argparse, math, os, shutil, subprocess, sys, tempfile
from datetime import datetime
from functools import wraps
from pathlib import Path
from time import perf_counter

try:
    import ezdxf
    from ezdxf import recover
    from ezdxf.math import Vec3
except ImportError:
    print("ERROR: ezdxf not installed")
    print("Install with: pip install ezdxf")
    sys.exit(1)

#---------------------------------------------------------------------------
# DEFAULTS

# Path to ODA File Converter
# Adjust this to your installation path
ODA_CONVERTER_PATHS = [
    r"C:\Program Files\ODA\ODAFileConverter 27.1.0\ODAFileConverter.exe",
    r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
    r"C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe",
    r"C:\ODA\ODAFileConverter\ODAFileConverter.exe",
]

DEFAULT_OUTPUT_DIR_SUFFIX = "PySimplified"

#---------------------------------------------------------------------------
# Classes

class File():
	'''
	Class for file name validation
	'''

	def __init__(self):
		''' '''
		print("\nWhy would you do that?..")

	@staticmethod
	def read(name, as_list: bool = False):
		'''
		This function reads from specified file

		Args:
			file_name (string): String representing a file name

		Return:
			list of strings
			or None if there were errors
		'''
		try:
			if not as_list:
				with open(name, "r", encoding="utf-8") as f:
					text = f.read()
					if len(text) == 0:										# If file is empty
						print("\nFile is empty")							# Let user know it
						return None											# And return None
					elif text.startswith("\ufeff"):							# If signed
						text = text.replace("\ufeff", '', 1)				# Unsign it
					else:
						return(text)										# Return text
			
			else:
				with open(name, "r", encoding="utf-8") as f:
					text_list = []
					for line in f:
						text_list.append(line.strip("\n"))
					if len(text_list) == 0:										# If file is empty
						print("\nFile is empty")								# Let user know it
						return None												# And return None
					elif text_list[0].startswith("\ufeff"):						# If signed
						text_list[0] = text_list[0].replace("\ufeff", '', 1)	# Unsign it
					else:
						return(text_list)										# Return list

		except FileNotFoundError:
			print ("\nFile not found")
			return None
		except Exception as e:
			print("\nSomething went wrong")
			print(e)
			return None

	@staticmethod
	def write(file_name, content, param = "w"):
		'''
		This function writes text in input file
		
		Args:
			file_name (string): String representing a file name
			content (list): A list of lines
		'''
		with open(file_name, param, encoding="utf-8") as f:
			f.write(content[0])
			for i in range(1, len(content)):
				f.write("\n" + content[i])



# NOTE: Used to track memory usage as well, but it slows the process down dramatically
class Profiler:
	'''
	A very basic profiler that analyzes execution time.
	Used to track memory usage as well, but it slows the process down dramatically.
	Unly uncomment it when you really NEED to analyze the memory usage.
	'''
	
	def __init__(self):
		self.enabled = True
		self.results = []
	
	def __call__(self, func):
		@wraps(func)
		def wrapper(*args, **kwargs):
			if not self.enabled:
				return func(*args, **kwargs)
			
			# tracemalloc.start()
			start = perf_counter()
			
			result = func(*args, **kwargs)
			duration = perf_counter() - start
			# current, peak = tracemalloc.get_traced_memory()
			# tracemalloc.stop()
			
			self.results.append({
				'function': func.__name__,
				'time': duration,
				# 'memory_peak': peak,
				'result': result
			})
			print(f"{func.__name__:>19s} | {duration:>7.3f} s") # | {peak / 1024 / 1024:6.2f} MB")
			
			return result
		
		return wrapper
	
	def summary(self):
		if not self.results:
			print("\n No profiling data collected\n")
			return
		
		times = [result['time'] for result in self.results]
		# memories = [result['memory_peak'] for result in self.results]
		
		print(f"\n{'='*67}")
		print(f"PROFILING SUMMARY ({len(self.results)} runs)")
		print(f"{'='*67}")
		print(f"{'Total time: ':>20} {sum(times):>8,.3f} s")
		print(f"{'Average time: ':>20} {sum(times) / len(times):>8,.3f} s")
		print(f"{'Min time: ':>20} {min(times):>8.3f} s")
		print(f"{'Max time: ':>20} {max(times):>8.3f} s")
		# print(f"Avg memory:   {sum(memories) / len(memories) / 1024 / 1024:.2f} MB")
		# print(f"Peak memory:  {max(memories) / 1024 / 1024:.2f} MB")
		print(f"{'='*67}")

#---------------------------------------------------------------------------
# Decorators
# Profiler
profiler = Profiler()

#---------------------------------------------------------------------------
# Func
def find_oda_converter():
    """Find ODA File Converter executable"""
    for path in ODA_CONVERTER_PATHS:
        if os.path.exists(path):
            return path
    
    print("ERROR: ODA File Converter not found!")
    print("Please install from: https://www.opendesign.com/guestfiles/oda_file_converter")
    print(f"Expected locations: {ODA_CONVERTER_PATHS}")
    sys.exit(1)


def convert_dwg_to_dxf(dwg_path, output_dir, oda_converter):
    """Convert DWG to DXF using ODA File Converter"""
    
    # ODA converter needs a specific folder structure
    input_dir = tempfile.mkdtemp(prefix="oda_input_")
    temp_output = tempfile.mkdtemp(prefix="oda_output_")
    
    try:
        # Copy DWG to temp input folder
        temp_dwg = os.path.join(input_dir, os.path.basename(dwg_path))
        shutil.copy2(dwg_path, temp_dwg)
        
        # Run ODA converter
        # Format: ODAFileConverter "input_folder" "output_folder" "output_version" "output_format" "recurse" "audit"
        cmd = [
            oda_converter,
            input_dir,
            temp_output,
            "ACAD2018",  # Output version
            "DXF",       # Output format
            "0",         # Don't recurse subdirectories
            "1"          # Audit and recover
        ]
        
        print(f"    Converting to DXF...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            print(f"    WARNING: ODA converter returned code {result.returncode}")
        
        # Find the converted DXF file
        dxf_name = Path(dwg_path).stem + ".dxf"
        temp_dxf = os.path.join(temp_output, dxf_name)
        
        if not os.path.exists(temp_dxf):
            raise FileNotFoundError(f"Converted DXF not found: {temp_dxf}")
        
        # Move to output directory
        output_dxf = os.path.join(output_dir, dxf_name)
        shutil.move(temp_dxf, output_dxf)
        
        return output_dxf
        
    finally:
        # Cleanup temp directories
        shutil.rmtree(input_dir, ignore_errors=True)
        shutil.rmtree(temp_output, ignore_errors=True)


def convert_dxf_to_dwg(dxf_path, output_dir, oda_converter):
    """Convert DXF back to DWG using ODA File Converter"""
    
    input_dir = tempfile.mkdtemp(prefix="oda_input_")
    temp_output = tempfile.mkdtemp(prefix="oda_output_")
    
    try:
        # Copy DXF to temp input folder
        temp_dxf = os.path.join(input_dir, os.path.basename(dxf_path))
        shutil.copy2(dxf_path, temp_dxf)
        
        # Run ODA converter
        cmd = [
            oda_converter,
            input_dir,
            temp_output,
            "ACAD2018",  # Output version
            "DWG",       # Output format
            "0",         # Don't recurse
            "1"          # Audit
        ]
        
        print(f"    Converting back to DWG...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode != 0:
            print(f"    WARNING: ODA converter returned code {result.returncode}")
        
        # Find the converted DWG file
        dwg_name = Path(dxf_path).stem + ".dwg"
        temp_dwg = os.path.join(temp_output, dwg_name)
        
        if not os.path.exists(temp_dwg):
            raise FileNotFoundError(f"Converted DWG not found: {temp_dwg}")
        
        # Move to output directory
        output_dwg = os.path.join(output_dir, dwg_name)
        shutil.move(temp_dwg, output_dwg)
        
        return output_dwg
        
    finally:
        shutil.rmtree(input_dir, ignore_errors=True)
        shutil.rmtree(temp_output, ignore_errors=True)


def distance_2d(p1, p2):
    """Calculate 2D distance between two points"""
    if hasattr(p1, 'x'):
        return math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)
    else:
        return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)


def remove_short_segments(points, min_length, remove_short=True, keep_short_segments=False):
    """
    Remove very short line segments from a point list.
    Keeps the overall shape by merging short segments with neighbors.
    
    Args:
        points: List of points (Vec3, tuples, or lists)
        min_length: Minimum segment length to keep
    
    Returns:
        Filtered list of points
    """
    if len(points) < 2:
        return points
    elif len(points) == 2:
        # Check if the single segment is too short
        if distance_2d(points[0], points[1]) <= min_length:
            return [points[0]]  # Keep only the start point
        else:
            return points
    
    # Convert all points to tuples for consistency
    point_list = []
    for p in points:
        if hasattr(p, 'x'):
            point_list.append((p.x, p.y))
        else:
            point_list.append((p[0], p[1]))
    
    if len(point_list) < 2:
        return point_list
    
    # Always keep first point
    filtered = [point_list[0]]
    
    for i in range(1, len(point_list)):
        current = point_list[i]
        last_kept = filtered[-1]
        
        dist = distance_2d(last_kept, current)
        
        # Keep point if distance is above threshold
        if dist >= min_length or keep_short_segments:
            filtered.append(current)
        # else: skip this point (merge with previous segment)
    

    # Always keep last point if it's different from the last kept point
    dist = distance_2d(filtered[-1], point_list[-1])
    if len(filtered) < 2 or dist > 0.0001:
        if len(filtered) == 0 or dist >= min_length:
            filtered.append(point_list[-1])
    
    # Ensure we have at least 2 points
    if len(filtered) < 2 and len(point_list) >= 2:
        filtered = [point_list[0], point_list[-1]]

    if remove_short:
        if len(filtered) == 2:
            total_length = distance_2d(filtered[0], filtered[1])
            if total_length <= min_length:
                return []                   # Return empty list to signal "delete this polyline"
        else:
            # Check if the total length of the polyline is too short
            total_length = sum(distance_2d(filtered[i], filtered[i+1]) for i in range(len(filtered)-1))
            if total_length <= min_length:
                return []                   # Return empty list to signal "delete this polyline"
    
    return filtered

def flatten_arc_to_lines(arc, max_segments=None, tolerance=0.9, segment_angle=None):
    """
    Convert an arc to line segments.
    
    Args:
        arc: ezdxf arc entity
        max_segments: Fixed number of segments (if specified)
        segment_angle: Maximum angle per segment in degrees (if max_segments not specified)
    
    Returns:
        List of points
    """
    try:
        if max_segments:
            points = list(arc.flattening(max_segments))
        elif segment_angle:
            # Calculate segments based on angle
            # Get arc span in degrees
            start_angle = arc.dxf.start_angle
            end_angle = arc.dxf.end_angle
            
            # Handle angle wrapping
            if end_angle < start_angle:
                arc_span = 360 - start_angle + end_angle
            else:
                arc_span = end_angle - start_angle
            
            # Calculate number of segments needed
            calc_segments = max(2, int(math.ceil(arc_span / segment_angle)))
            points = list(arc.flattening(calc_segments))
        else:
            # Default: adaptive
            points = list(arc.flattening(segments=8))
        
        return points
    except Exception as e:
        print(f"      Warning: Arc flattening failed: {e}")
        return None

def flatten_spline_to_lines(spline, flattening_method='adaptive', max_segments=2, tolerance=0.9):
    """
    Convert a spline to line segments with different flattening strategies.
    
    Args:
        spline: ezdxf spline entity
        flattening_method: 'adaptive', 'fixed', or 'tolerance'
        max_segments: Maximum number of segments (for 'fixed' method)
        tolerance: Maximum deviation from curve (for 'adaptive' and 'tolerance' methods)
    
    Returns:
        List of points
    """
    try:
        if flattening_method == 'fixed' and max_segments:
            # Fixed number of segments - evenly spaced along spline
            # Use flattening with high segment count, then downsample
            points = list(spline.flattening(distance=tolerance, segments=max_segments * 2))
            
            # Downsample to exact number of segments
            if len(points) > max_segments + 1:
                step = len(points) / (max_segments + 1)
                indices = [int(i * step) for i in range(max_segments + 1)]
                points = [points[i] for i in indices]
            
            return points
            
        elif flattening_method == 'tolerance':
            # Tolerance-based: adaptive sampling based on curve complexity
            # Lower distance = more points in curved areas
            points = list(spline.flattening(distance=tolerance, segments=4))
            return points
            
        else:  # 'adaptive' (default)
            # Adaptive: balance between tolerance and minimum segments
            min_segments = max_segments if max_segments else 10
            points = list(spline.flattening(distance=tolerance, segments=min_segments))
            return points
            
    except Exception as e:
        # Fallback: use control points
        try:
            return list(spline.control_points)
        except:
            return None


def flatten_ellipse_to_lines(ellipse, num_segments=16):
    """
    Convert an ellipse to line segments.
    
    Args:
        ellipse: ezdxf ellipse entity
        num_segments: Number of segments (higher = smoother)
    
    Returns:
        List of points
    """
    try:
        # For ellipses, fixed segment count makes more sense
        # Calculate distance parameter based on desired segments
        # Smaller distance = more segments
        distance = 1.6 / num_segments
        points = list(ellipse.flattening(distance=distance, segments=num_segments))
        return points
    except Exception as e:
        print(f"      Warning: Ellipse flattening failed: {e}")
        return None


def simplify_polyline_vertices(polyline, min_segment_length, keep_short_segments=False):
    """
    Remove short segments from existing polylines.
    Modifies the polyline in-place.
    
    Args:
        polyline: ezdxf polyline entity (LWPOLYLINE or POLYLINE)
        min_segment_length: Minimum segment length to keep
        keep_short_segments: Whether to keep short segments
    
    Returns:
        Number of vertices removed
    """
    try:
        # Get current points
        if polyline.dxftype() == 'LWPOLYLINE':
            points = list(polyline.get_points('xy'))
        else:
            points = [(v[0], v[1]) for v in polyline.points()]
        
        if len(points) < 2:
            return 0
        
        # Filter short segments
        filtered = remove_short_segments(points, min_segment_length)
        
        removed_count = len(points) - len(filtered)
        
        if removed_count > 0:
            # Update polyline with filtered points
            if polyline.dxftype() == 'LWPOLYLINE':
                polyline.set_points(filtered)
            else:
                # For POLYLINE, we need to recreate vertices
                # This is more complex, skip for now
                pass
        
        return removed_count
        
    except Exception as e:
        print(f"      Warning: Could not simplify polyline: {e}")
        return 0


def remove_duplicate_points(points, tolerance=0.0001):
    """
    Remove consecutive duplicate points.
    
    Args:
        points: List of points
        tolerance: Distance below which points are considered duplicates
    
    Returns:
        Filtered list of points
    """
    if len(points) < 2:
        return points
    
    filtered = [points[0]]
    
    for i in range(1, len(points)):
        if distance_2d(filtered[-1], points[i]) > tolerance:
            filtered.append(points[i])
    
    return filtered

#---------------------------------------------------------------
# Main process loop

def process_dxf(dxf_path, output_path, config):
    """
    Process DXF file: convert splines to polylines and remove short segments.
    
    Args:
        dxf_path: Input DXF file path
        output_path: Output DXF file path
        config: Dictionary with processing parameters:
            - spline_method: 'adaptive', 'fixed', or 'tolerance'
            - spline_segments: Number of segments (for 'fixed' method)
            - spline_tolerance: Deviation tolerance (for other methods)
            - ellipse_segments: Number of segments for ellipses
            - min_line_length: Minimum length for line segments
            - simplify_existing: Whether to simplify existing polylines
    """
    
    print(f"  Loading DXF...")
    
    try:
        # Try normal load first
        doc = ezdxf.readfile(dxf_path)
    except:
        # If that fails, try recovery mode
        print(f"  Using recovery mode...")
        doc, auditor = recover.readfile(dxf_path)
        if auditor.has_errors:
            print(f"    Recovered with {len(auditor.errors)} errors")
    
    msp = doc.modelspace()
    
    # Count entities
    all_entities = list(msp)
    total_before = len(all_entities)
    
    arcs = [e for e in all_entities if e.dxftype() == 'ARC']
    splines = [e for e in all_entities if e.dxftype() == 'SPLINE']
    ellipses = [e for e in all_entities if e.dxftype() == 'ELLIPSE']
    polylines = [e for e in all_entities if e.dxftype() in ('LWPOLYLINE', 'POLYLINE')]
    lines = [e for e in all_entities if e.dxftype() == 'LINE']
    
    print(f"  Entities: {total_before}")
    print(f"  Arcs: {len(arcs)}")
    print(f"  Splines: {len(splines)}")
    print(f"  Ellipses: {len(ellipses)}")
    print(f"  Polylines: {len(polylines)}")
    print(f"  Lines: {len(lines)}")
    
    converted_count = 0
    failed_count = 0
    
    #------------------------------------------
    # Convert arcs to polylines
    if len(arcs) > 0:
        print(f"  Converting {len(arcs)} arcs...")
        
        for arc in arcs:
            try:
                layer = arc.dxf.layer
                color = arc.dxf.color if arc.dxf.hasattr('color') else 256
                
                points = flatten_arc_to_lines(
                    arc,
                    max_segments=config.get('arc_segments', None),
                    segment_angle=config.get('arc_segment_angle', 30)
                )
                
                if points and len(points) >= 2:
                    points = remove_duplicate_points(points)
                    
                    if config.get('min_line_length', 0) > 0:
                        points = remove_short_segments(points, config['min_line_length'])
                        
                        if len(points) < 2:
                            msp.delete_entity(arc)
                            converted_count += 1
                            continue
                    
                    point_tuples = [(p.x, p.y) if hasattr(p, 'x') else (p[0], p[1]) for p in points]
                    
                    if len(point_tuples) >= 2:
                        msp.add_lwpolyline(
                            point_tuples,
                            dxfattribs={
                                'layer': layer,
                                'color': color
                            }
                        )
                        
                        msp.delete_entity(arc)
                        converted_count += 1
                    else:
                        failed_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                print(f"    Warning: Failed to convert arc: {e}")
                failed_count += 1

    #------------------------------------------
    # Convert splines to polylines
    if len(splines) > 0:
        print(f"  Converting {len(splines)} splines (method: {config['spline_method']})...")
        
        for i, spline in enumerate(splines):
            if (i % 500 == 0 and i > 0) or i == len(splines) - 1:
                print(f"    Progress: {i}/{len(splines)}")
            
            try:
                layer = spline.dxf.layer
                color = spline.dxf.color if spline.dxf.hasattr('color') else 256
                
                # Flatten spline to points
                points = flatten_spline_to_lines(
                    spline,
                    flattening_method = config['spline_method'],
                    max_segments = config.get('spline_segments', 2),
                    tolerance = config.get('spline_tolerance', 0.01)
                )
                
                if points and len(points) >= 2:
                    # Remove duplicate consecutive points
                    points = remove_duplicate_points(points)
                    
                    # Remove short segments if configured
                    if config.get('min_line_length', 0) > 0 and not config.get('keep_short_segments', False):
                        points = remove_short_segments(points, config['min_line_length'])
                        if len(points) < 2:
                            msp.delete_entity(spline)
                            converted_count += 1
                            continue
                    
                    # Convert to tuples
                    point_tuples = [(p.x, p.y) if hasattr(p, 'x') else (p[0], p[1]) for p in points]
                    
                    if len(point_tuples) >= 2:
                        msp.add_lwpolyline(
                            point_tuples,
                            dxfattribs = {
                                'layer': layer,
                                'color': color
                            }
                        )
                        
                        msp.delete_entity(spline)
                        converted_count += 1
                    else:
                        failed_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                print(f"    Warning: Failed to convert spline #{i}: {e}")
                failed_count += 1
    
    #------------------------------------------
    # Convert ellipses to polylines
    if len(ellipses) > 0:
        print(f"  Converting {len(ellipses)} ellipses...")
        
        for ellipse in ellipses:
            try:
                layer = ellipse.dxf.layer
                color = ellipse.dxf.color if ellipse.dxf.hasattr('color') else 256
                
                points = flatten_ellipse_to_lines(ellipse, config.get('ellipse_segments', 16))
                
                if points and len(points) >= 2:
                    points = remove_duplicate_points(points)
                    
                    if config.get('min_line_length', 0) > 0 and not config.get('keep_short_segments', False):
                        points = remove_short_segments(points, config['min_line_length'])
                        if len(points) < 2:
                            msp.delete_entity(ellipse)
                            converted_count += 1
                            continue
                    
                    point_tuples = [(p.x, p.y) if hasattr(p, 'x') else (p[0], p[1]) for p in points]
                    
                    if len(point_tuples) >= 2:
                        msp.add_lwpolyline(
                            point_tuples,
                            dxfattribs = {
                                'layer': layer,
                                'color': color,
                                'closed': True
                            }
                        )
                        
                        msp.delete_entity(ellipse)
                        converted_count += 1
                    else:
                        failed_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                print(f"    Warning: Failed to convert ellipse: {e}")
                failed_count += 1
    
    #------------------------------------------
    # Simplify existing polylines (remove short segments)
    if config.get('simplify_existing', False) and len(polylines) > 0:
        print(f"  Simplifying {len(polylines)} existing polylines...")
        
        total_vertices_removed = 0
        for polyline in polylines:
            removed = simplify_polyline_vertices(polyline, config['min_line_length'], config.get('keep_short_segments', False))
            total_vertices_removed += removed
        
        print(f"    Removed {total_vertices_removed} short segments")
    
    #------------------------------------------
    # Remove short LINE entities
    if config.get('min_line_length', 0) > 0 and len(lines) > 0:
        print(f"  Removing short LINE entities...")
        
        removed_lines = 0
        for line in lines:
            try:
                start = (line.dxf.start.x, line.dxf.start.y)
                end = (line.dxf.end.x, line.dxf.end.y)
                length = distance_2d(start, end)
                
                if length <= config['min_line_length']:
                    msp.delete_entity(line)
                    removed_lines += 1
            except:
                pass
        
        print(f"    Removed {removed_lines} short lines")
    
    print(f"  Converted: {converted_count}")
    if failed_count > 0:
        print(f"  Failed: {failed_count}")
    
    # Purge unused items
    # print(f"  Purging unused items...")
    # doc.layers.purge()
    # doc.linetypes.purge()
    # doc.styles.purge()
    
    # Audit and fix
    auditor = doc.audit()
    if auditor.has_errors:
        print(f"  Fixed {len(auditor.errors)} errors")
    
    # Final count
    final_count = len(list(msp))
    print(f"  Final entity count: {final_count}")
    
    # Save
    print(f"  Saving DXF...")
    doc.saveas(output_path)
    
    return True

@profiler
def process_dwg(dwg_path, output_path, oda_converter, config, keep_temp=False):
    """Process a DWG file: DWG -> DXF -> Process -> DWG"""
    
    temp_dir = tempfile.mkdtemp(prefix="dwg_process_")
    
    try:
        # Step 1: Convert DWG to DXF
        dxf_path = convert_dwg_to_dxf(dwg_path, temp_dir, oda_converter)
        
        # Step 2: Process DXF (simplify splines and remove short lines)
        processed_dxf = os.path.join(temp_dir, "processed.dxf")
        process_dxf(dxf_path, processed_dxf, config)
        
        # Step 3: Convert back to DWG
        output_dir = os.path.dirname(output_path)
        final_dwg = convert_dxf_to_dwg(processed_dxf, output_dir, oda_converter)
        
        # Rename to desired output name if different
        if final_dwg != output_path:
            if os.path.exists(output_path):
                os.remove(output_path)
            shutil.move(final_dwg, output_path)
        
        print(f"  ✓ Complete")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if not keep_temp:
            shutil.rmtree(temp_dir, ignore_errors=True)

def display_config(oda_converter, config):
    print(f"Using ODA File Converter: {oda_converter}")
    print(f"Configuration:")
    print(f"  Spline method: {config['spline_method']}")
    print(f"  Spline segments: {config['spline_segments']}")
    print(f"  Spline tolerance: {config['spline_tolerance']}")
    print(f"  Ellipse segments: {config['ellipse_segments']}")
    print(f"  Min line length: {config['min_line_length']}")
    print(f"  Simplify existing: {config['simplify_existing']}")
    print(f"  Keep short segments: {config['keep_short_segments']}")
    print()

def get_output_dir(input_folder, args) -> Path:
    if args.in_place:
        output_folder = input_folder
    elif args.output:
        output_folder = Path(args.output)
        output_folder.mkdir(parents=True, exist_ok=True)
    else:
        output_folder = input_folder / DEFAULT_OUTPUT_DIR_SUFFIX
        output_folder.mkdir(exist_ok=True)
        time_current = datetime.now()
        output_folder = output_folder / time_current.strftime("%y-%m-%d_%H-%M-%S")
        output_folder.mkdir(parents=True, exist_ok=True)
    
    return output_folder

def process_folder(input_folder, output_folder, oda_converter, config, args):
    """Process all DWG files in a folder"""
    
    input_folder = Path(input_folder)
    output_folder = Path(output_folder)
    
    if not input_folder.exists():
        print(f"ERROR: Input folder does not exist: {input_folder}")
        return
    
    dwg_files = list(input_folder.glob("*.dwg"))
    
    if not dwg_files or len(dwg_files) == 0:
        print(f"No DWG files found in: {input_folder}")
        return
    
    print(f"Found {len(dwg_files)} DWG files(s)\n")
    # Process files
    success_count = 0

    for dwg_file in dwg_files:
        print(f"\nProcessing: {dwg_file.name}")
        
        if args.in_place:
            if args.backup:
                backup_path = str(dwg_file) + ".bak"
                shutil.copy2(dwg_file, backup_path)
                print(f"  Backup: {backup_path}")
            output_path = dwg_file
        else:
            if args.clean_names:
                output_path = output_folder / dwg_file.name
            else:
                output_path = output_folder / str("t_" + str(config['spline_tolerance']) +
                                            "_s_" + str(config['spline_segments']) +
                                            "_ll_" + str(config['min_line_length']) +
                                            "_" + dwg_file.name)
        
        if process_dwg(str(dwg_file), str(output_path), oda_converter, config, args.keep_temp):
            success_count += 1
            print(f"Saved simplified DWG to: {output_path}")
        else:
            print(f"Failed to process: {dwg_file.name}")

        print()

     # Summary
    print("=" * 50)
    print(f"COMPLETE: {success_count}/{len(dwg_files)} files processed")
    print("=" * 50)
    
    if args.profiler:
        profiler.summary()

def log_config_to_file(output_folder, config, args=None):
    """
    Log all configuration parameters to a file in the output directory.
    
    Args:
        output_folder: Path object or string of the output directory
        config: Dictionary containing processing configuration
        args: Optional argparse Namespace with command-line arguments
    """
    timestamp = datetime.now().strftime("%y-%m-%d_%H-%M-%S")
    config_file = Path(output_folder) / f"config_{timestamp}.txt"

    log_lines = []
    log_lines.append("DWG Processing Configuration")
    log_lines.append("=" * 30) 
    log_lines.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    log_lines.append("=" * 30 + "\n")
    
    log_lines.append("Configuration Parameters:")
    log_lines.append("-" * 30 + "")
    for key, value in config.items():
        log_lines.append(f"  {key}: {value}")
    
    if args:
        log_lines.append("\n" + "=" * 30)
        log_lines.append("Command-line Arguments:")
        log_lines.append("-" * 30)
        for key, value in vars(args).items():
            log_lines.append(f"  {key}: {value}")
    
    log_lines.append("\n" + "=" * 30)

    File.write(config_file, log_lines, param="a")
    
    # with open(config_file, 'w') as f:
    #     f.write("DWG Processing Configuration\n")
    #     f.write("=" * 50 + "\n")
    #     f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    #     f.write("=" * 50 + "\n\n")
        
    #     f.write("Configuration Parameters:\n")
    #     f.write("-" * 50 + "\n")
    #     for key, value in config.items():
    #         f.write(f"  {key}: {value}\n")
        
    #     if args:
    #         f.write("\n" + "=" * 50 + "\n")
    #         f.write("Command-line Arguments:\n")
    #         f.write("-" * 50 + "\n")
    #         for key, value in vars(args).items():
    #             f.write(f"  {key}: {value}\n")
        
    #     f.write("\n" + "=" * 50 + "\n")
    
    print(f"  Config logged to: {config_file}")

def parse_arguments():
    parser = argparse.ArgumentParser(description    = "Simplify DWG files by converting splines to polylines and removing short segments",
                                    formatter_class = argparse.RawDescriptionHelpFormatter,
                                            epilog  = """
Spline flattening methods:
  adaptive  - Balance between tolerance and minimum segments (default)
  fixed     - Exact number of segments per spline (use with --spline-segments)
  tolerance - Adaptive based only on deviation tolerance (use with --spline-tolerance)

Examples:
  # Adaptive method with 20 segments minimum
  python simplify_dwg.py input_folder --spline-method adaptive --spline-segments 20
  
  # Fixed 3 segments per spline
  python simplify_dwg.py input_folder --spline-method fixed --spline-segments 3
  
  # Tolerance-based with 0.01 deviation
  python simplify_dwg.py input_folder --spline-method tolerance --spline-tolerance 0.01
  
  # Remove lines shorter than 0.1 units
  python simplify_dwg.py input_folder --min-line-length 0.1
        """
    )
    
    parser.add_argument('input_folder', help='Folder containing DWG files')
    parser.add_argument('-o', '--output', help='Output folder (default: input_folder/PySimplified)')
    parser.add_argument('-i', '--in-place', action='store_true', help='Process files in-place')
    parser.add_argument('-b', '--backup', action='store_true', help='Create .bak backups (with --in-place)')
    parser.add_argument('--clean-names', action='store_true', 
                        help='Keep the names clean by removing distance and tolerance from output file names')
    
    # Arc conversion options
    parser.add_argument('--arc-segments', type=int, default=None,
                        help='Fixed number of segments for arcs (default: None = adaptive)')
    parser.add_argument('--arc-segment-angle', type=float, default=30.0,
                        help='Maximum angle per arc segment in degrees (default: 30.0)')

    # Spline conversion options
    parser.add_argument('--spline-method', choices=['adaptive', 'fixed', 'tolerance'], 
                        default='adaptive', help='Spline flattening method (default: adaptive)')
    parser.add_argument('--spline-segments', type=int, default=2, 
                        help='Number of segments for splines (default: 2)')
    parser.add_argument('--spline-tolerance', type=float, default=0.9, 
                        help='Deviation tolerance for spline flattening (default: 0.9)')
    
    # Ellipse options
    parser.add_argument('--ellipse-segments', type=int, default=16, 
                        help='Number of segments for ellipses (default: 16)')
    
    # Line simplification options
    parser.add_argument('--min-line-length', type=float, default=0.0, 
                        help='Minimum line segment length - shorter segments removed (default: 0 = disabled)')
    parser.add_argument('--simplify-existing', action='store_true', 
                        help='Also simplify existing polylines')
    parser.add_argument('--keep-short-segments', action='store_true', 
                        help='Keep short line segments')
    
    
    # Other options
    parser.add_argument('--keep-temp', action='store_true', help='Keep temporary files for debugging')
    parser.add_argument('--oda-path', help='Path to ODA File Converter executable')
    parser.add_argument('-P', "--profiler",  action = "store_true", default = False,
					 help = "Enable profiler")
    
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    # Build configuration
    config = {
        'arc_segments': args.arc_segments,
        'arc_segment_angle': args.arc_segment_angle,
        'spline_method': args.spline_method,
        'spline_segments': args.spline_segments,
        'spline_tolerance': args.spline_tolerance,
        'ellipse_segments': args.ellipse_segments,
        'min_line_length': args.min_line_length,
        'simplify_existing': args.simplify_existing,
        'keep_short_segments': args.keep_short_segments,
    }
    
    # Find ODA converter
    if args.oda_path:
        oda_converter = args.oda_path
        if not os.path.exists(oda_converter):
            print(f"ERROR: ODA converter not found at: {oda_converter}")
            sys.exit(1)
    else:
        oda_converter = find_oda_converter()
        
    display_config(oda_converter, config)

    if args.profiler:
        profiler.enabled = True
    else:
        profiler.enabled = False

    
    # Setup paths
    input_folder = Path(args.input_folder)
    
    if not input_folder.exists():
        print(f"ERROR: Input folder not found: {input_folder}")
        sys.exit(1)

    output_folder = get_output_dir(input_folder, args)
    
    log_config_to_file(output_folder, config, args)

    process_folder(input_folder, output_folder, oda_converter, config, args)


if __name__ == "__main__":
    main()