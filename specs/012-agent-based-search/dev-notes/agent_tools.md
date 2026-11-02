# Journey Agent Tools

All read-only over `Stop` / `Route` / `RouteStopMembership`.
Return `{"ok": True, ...}` or `{"ok": False, "error": ...}`. Never raise.

## Existing, keep as-is

### `search_stops(query|bbox)`

Purpose: flat stop lookup for exact ids.
Use: first name-to-id resolution, selection follow-ups.
Output: `{"ok","status":"ok|empty|zoom_in","stops":[{id,name,name_ml,lat,lon}]}`.

### `find_routes(from_stop_id,to_stop_id)`

Purpose: single-pair direct check with `pos_from < pos_to`.
Use: leaf verifier only, retained for other use. Not an agent entry path; agent answers MUST go via `find_routes_matrix`.
Output: `{"ok","routes":[{id,name,origin,destination,operator,network,evidence}]}`.

### `get_route_detail(route_id)`

Purpose: ordered stops + evidence for verifier and citation.
Use: every cited route re-checked here.
Output: `{"ok","route":{id,name,origin,destination,operator,network,evidence,stops:[{stop,position,is_origin,is_terminus}]}}`.

## Existing, promote to model

### `search_places(query|bbox)` — existing, wire to agent

Purpose: group same-name stops by `casefold` name + `150m` single-linkage haversine.
Use: agent calls before asking user. `kaloor#1={K1,K2,K3}`, `kaloor#2={K4,K5}`.
Output: `{"ok","status":"ok","groups":[{key,label,center,bbox,spread_m,members[{id,name,lat,lon}],route_count,routes[{id,name}]}]}`.
Change: add to `TOOL_SCHEMAS` + `_TOOL_FUNCTIONS`. No logic change.

### `find_routes_matrix(from_ids,to_ids)` — existing, wire to agent

Purpose: batch exact-pair test. Skips `from==to`. Drops opposite direction.
Use: test all origin-group x destination-group members at once.
Output: `{"ok","pairs":[{from_stop_id,to_stop_id,routes[{id,name,evidence}]}]}`.
Change: add to `TOOL_SCHEMAS` + `_TOOL_FUNCTIONS`. No logic change.

## New, create

### `distance_m(lat1,lon1,lat2,lon2)`

Purpose: let agent test `d(K1,K2)` without guessing.
Use: classify walkable mate inside group, e.g. $d \le 150m$.
Output: `{"ok":True,"distance_m":20.4}`.
New file code in `tools.py`, pure haversine, SQLite-portable.

### `nearby_stops(lat,lon,radius_m)` — create now for location

Purpose: origin from shared location and `500m` walkable search for far stops.
Use: location present replaces `search_places(query)` for that end; same use for `kaloor#2` onward search.
Output: `{"ok","stops":[{id,name,lat,lon,distance_m}]}` ordered by distance.
New function in `tools.py`, capped at 100, same `zoom_in` guard as `search_stops`.

## Update

`_group_routes()`: keep union `route_count` for display, but agent MUST NOT treat group count as proof for exact member. Proof always comes from matrix + `get_route_detail`.
