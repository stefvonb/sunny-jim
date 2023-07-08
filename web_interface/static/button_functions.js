function httpRequest(address, reqType, asyncProc) {
    var req = window.XMLHttpRequest ? new XMLHttpRequest() : new ActiveXObject("Microsoft.XMLHTTP");
    if (asyncProc) {
        req.onreadystatechange = function () {
            if (this.readyState == 4) {
                asyncProc(this);
            }
        };
    }
    req.open(reqType, address, !(!asyncProc));
    req.send();
    return req;
}

function switch_to_line_mode(server_ip, server_port, device_name = "inverter") {
    // Set the button to loading state
    const line_mode_button = document.getElementById("line-mode-btn");

    line_mode_button.classList.add("disabled");
    line_mode_button.disabled = true;

    const address = `http://${server_ip}:${server_port}/devices/control/${device_name}/SWITCH_TO_LINE_MODE/`;
    var req = httpRequest(address, "PUT");

    // Set the button back to normal state
    line_mode_button.classList.remove("disabled");
    line_mode_button.disabled = false;

    control_update = document.getElementById("control-update");
    if (req.status != 200) {
        control_update.innerHTML = "Failed to switch to line mode!";
        control_update.classList.remove("text-muted");
        control_update.classList.remove("text-success");
        control_update.classList.add("text-danger");
    } else {
        control_update.innerHTML = "Switched to line mode (this may take a few seconds to update).";
        control_update.classList.remove("text-muted");
        control_update.classList.remove("text-danger");
        control_update.classList.add("text-success");
    }
}

function switch_to_battery_mode(server_ip, server_port, device_name = "inverter") {
    // Set the button to loading state
    const battery_mode_button = document.getElementById("battery-mode-btn");

    battery_mode_button.classList.add("disabled");
    battery_mode_button.disabled = true;

    const address = `http://${server_ip}:${server_port}/devices/control/${device_name}/SWITCH_TO_BATTERY_MODE/`;
    var req = httpRequest(address, "PUT");

    // Set the button back to normal state
    battery_mode_button.classList.remove("disabled");
    battery_mode_button.disabled = false;

    control_update = document.getElementById("control-update");
    if (req.status != 200) {
        control_update.innerHTML = "Failed to switch to battery mode!";
        control_update.classList.remove("text-muted");
        control_update.classList.remove("text-success");
        control_update.classList.add("text-danger");
    } else {
        control_update.innerHTML = "Switched to battery mode (this may take a few seconds to update).";
        control_update.classList.remove("text-muted");
        control_update.classList.remove("text-danger");
        control_update.classList.add("text-success");
    }
}

function turn_off_grid_charging(server_ip, server_port, device_name = "inverter") {
    // Set the button to loading state
    const grid_charging_button = document.getElementById("turn-off-grid-btn");

    grid_charging_button.classList.add("disabled");
    grid_charging_button.disabled = true;

    const address = `http://${server_ip}:${server_port}/devices/control/${device_name}/TURN_OFF_GRID_CHARGING/`;
    var req = httpRequest(address, "PUT");

    // Set the button back to normal state
    grid_charging_button.classList.remove("disabled");
    grid_charging_button.disabled = false;

    control_update = document.getElementById("control-update");
    if (req.status != 200) {
        control_update.innerHTML = "Failed to turn off grid charging!";
        control_update.classList.remove("text-muted");
        control_update.classList.remove("text-success");
        control_update.classList.add("text-danger");
    } else {
        control_update.innerHTML = "Turned off grid charging.";
        control_update.classList.remove("text-muted");
        control_update.classList.remove("text-danger");
        control_update.classList.add("text-success");
    }
}

function turn_on_grid_charging(server_ip, server_port) {
    // Set the button to loading state
    const grid_charging_button = document.getElementById("charge-grid-btn");

    grid_charging_button.classList.add("disabled");
    grid_charging_button.disabled = true;

    // Get the charge current
    const charge_current = document.getElementById("charge-current-value").value;

    var address = `http://${server_ip}:${server_port}/devices/control/charge_inverter_from_grid/`;
    if (charge_current != "")
        address += `?charge_current=${charge_current}`;

    var req = httpRequest(address, "PUT");

    // Set the button back to normal state
    grid_charging_button.classList.remove("disabled");
    grid_charging_button.disabled = false;

    control_update = document.getElementById("control-update");
    if (req.status != 200) {
        control_update.innerHTML = "Failed to turn on grid charging!";
        control_update.classList.remove("text-muted");
        control_update.classList.remove("text-success");
        control_update.classList.add("text-danger");
    } else {
        control_update.innerHTML = "Turned on grid charging.";
        control_update.classList.remove("text-muted");
        control_update.classList.remove("text-danger");
        control_update.classList.add("text-success");
    }
}