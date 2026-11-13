# Access fees across a partitioned floor

The floor is the integer unit cells 0<=x<width, 0<=y<height, with size=[width,height]. entry is the coordinate pair of a free starting cell. Rectangles [x0,y0,x1,y1] in blocked cover cells whose lower-left coordinates are in the half-open rectangle. Walls are zero-thickness horizontal or vertical segments on cell boundaries, listed as {segment:[x0,y0,x1,y1],fee}. A wall never occupies area. Coordinates are integral, and maps can have large coordinate extents.

Movement between free cells is across a shared unit side; no diagonal movement. Normally crossing is free. Each wall covering the shared side charges its nonnegative integer fee each time it is crossed. Overlapping walls charge the sum; any null fee makes crossing that side impossible. An edge touching only a wall endpoint is free of that wall's fee. The floor boundaries cannot be crossed.

For each free cell find the minimum total fee from entry. Return {area_by_fee,unreachable}. area_by_fee maps each attained cost, as a decimal string, to total reachable floor area with precisely that minimum cost. unreachable is the total area of free cells unreachable by any route. Exclude blocked area.
