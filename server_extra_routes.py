@app.get("/accounts/results")
async def get_results():
    """Return last session results from the database."""
    try:
        if state.current_session_id:
            result = state.db.client.table('session_results') \
                .select('*') \
                .eq('session_id', state.current_session_id) \
                .order('created_at', desc=True) \
                .limit(500) \
                .execute()
            return result.data or []
    except Exception:
        pass
    return []

@app.get("/vpn/status")
async def vpn_status():
    """Return current VPN status."""
    try:
        is_connected, location = state.vpn_manager.get_status()
        return {"connected": bool(is_connected), "location": location}
    except Exception:
        return {"connected": False, "location": None}

@app.post("/vpn/connect")
async def vpn_connect(location: str = None):
    """Connect to VPN, optionally at a given location."""
    try:
        if location:
            success, msg = state.vpn_manager.connect(location)
        else:
            success, msg = state.vpn_manager.connect_random_location()
        return {"success": success, "message": msg}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/vpn/disconnect")
async def vpn_disconnect():
    """Disconnect VPN."""
    try:
        state.vpn_manager.disconnect()
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.get("/vpn/locations")
async def vpn_locations():
    """Return available VPN locations."""
    try:
        locs = state.vpn_manager.list_locations()
        return locs or []
    except Exception:
        return []
