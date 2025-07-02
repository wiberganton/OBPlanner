# Scan Settings Documentation

This document outlines the various scan strategies and their corresponding settings.
The strategy is a str while the corresponding settings should be in the form of a dictionary

## Infill strategies
The following scan strategies are supported:
- `LineSort`: Simple line scanning left-right-left-.., 
- `LineSnake`: Simple line scanning left-right,left-right,.., 
- `LineConcentric` : Moving in full circles along the contour with a point_distance distance between each line, with constant speed.
- `SpotRandom`: Spot melting with random order of spots.
- `SpotOrdered`: Spot melting jumping along the lines with some predefined distance.

### LineSnake
No settings

### LineSort
No settings

### LineConcentric
| Setting Key | Data Type | Description                                         | Example Value   |
|-------------|-----------|-----------------------------------------------------|-----------------|
| direction   | str       | Starting from center out or from outer in (standard)| inward/ outward |

### SpotRandom
| Setting Key | Data Type | Description                                           | Example Value |
|-------------|-----------|-------------------------------------------------------|---------------|
| seed        | int       | Seed for random (not mandatory)                       | 4             |

### SpotOrdered
| Setting Key | Data Type | Description                                           | Example Value |
|-------------|-----------|-------------------------------------------------------|---------------|
| x_jump      | int       | Number of points that should be jumped in x direction | 2             |
| y_jump      | int       | Number of points that should be jumped in x direction | 5             |

## Contour strategies
The following scan strategies are supported:
- `line_simple`: Simple line scanning, with constant speed.
- `point_simple`: Simple spot scanning.

Please ensure you use the correct settings for the selected scan strategy. Providing incorrect or invalid settings may result in unexpected behavior or errors.
