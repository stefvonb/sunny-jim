function startWebsocketListener(server, port) {
  window.addEventListener("DOMContentLoaded", () => {
    const websocket = new WebSocket(`ws://${server}:${port}/`);
    websocket.onmessage = ({ data }) => {
      // Parse the data
      const device_json = JSON.parse(data);
      const device_info = device_json.device_info;
      const device_state = device_json.device_state;

      // Inverter related info
      if (device_info.device_type == "inverter") {
        // Update the grid-status span
        const grid_status = document.getElementById("grid-status");
        if (device_state.grid_state == "on") {
          grid_status.classList.remove("bg-danger");
          grid_status.classList.add("bg-success");
        } else {
          grid_status.classList.remove("bg-success");
          grid_status.classList.add("bg-danger");
        }
        grid_status.innerHTML = device_state.grid_state.toUpperCase();

        // Update the output-mode span
        const output_mode = document.getElementById("output-mode");
        if (device_state.output_mode == "line") {
          output_mode.classList.remove("bg-success");
          output_mode.classList.add("bg-info");
        }
        else {
          output_mode.classList.remove("bg-info");
          output_mode.classList.add("bg-success");
        }
        output_mode.innerHTML = device_state.output_mode.toUpperCase();

        // Update the output-voltage span
        const output_voltage = document.getElementById("output-voltage");
        output_voltage.innerHTML = device_state.output_voltage.toFixed(1) + "V";

        // Update the output-frequency span
        const output_frequency = document.getElementById("output-frequency");
        output_frequency.innerHTML = device_state.output_frequency.toFixed(1) + "Hz";

        // Update the selected-mode span
        const selected_mode = document.getElementById("selected-mode");
        if (device_state.selected_mode == "line") {
          selected_mode.classList.remove("bg-success");
          selected_mode.classList.add("bg-info");
        }
        else {
          selected_mode.classList.remove("bg-info");
          selected_mode.classList.add("bg-success");
        }
        selected_mode.innerHTML = device_state.selected_mode.toUpperCase();

        // Update the selected-charger span
        const selected_charger = document.getElementById("selected-charger");
        if (device_state.selected_charger == "solar") {
          selected_charger.classList.remove("bg-info");
          selected_charger.classList.add("bg-warning");
        }
        else {
          selected_charger.classList.remove("bg-warning");
          selected_charger.classList.add("bg-info");
        }
        selected_charger.innerHTML = device_state.selected_charger.toUpperCase();

        // Update the PV input power span
        const pv_input_power = document.getElementById("pv-input");
        var pv_input_power_value = device_state.pv_input_power;
        if (pv_input_power_value < 200) {
          pv_input_power.classList.remove("text-body");
          pv_input_power.classList.remove("text-body-secondary");
          pv_input_power.classList.add("text-body-tertiary");
        } else if (pv_input_power_value < 800) {
          pv_input_power.classList.remove("text-body-tertiary");
          pv_input_power.classList.remove("text-body");
          pv_input_power.classList.add("text-body-secondary");
        } else {
          pv_input_power.classList.remove("text-body-tertiary");
          pv_input_power.classList.remove("text-body-secondary");
          pv_input_power.classList.add("text-body");
        }
        pv_input_power.innerHTML = pv_input_power_value.toFixed(0) + "W";

        // Update the load span
        const load = document.getElementById("load-power");
        const load_progress_bar = document.getElementById("load-power-progress-bar");
        var load_value = device_state.load_power;
        var load_percentage = device_state.load_percentage;
        if (load_percentage < 0.2) {
          load.classList.remove("text-warning");
          load.classList.remove("text-danger");
          load.classList.add("text-body");

          load_progress_bar.classList.remove("bg-warning");
          load_progress_bar.classList.remove("bg-danger");
        } else if (load_percentage < 0.6) {
          load.classList.remove("text-body");
          load.classList.remove("text-danger");
          load.classList.add("text-warning");

          load_progress_bar.classList.remove("bg-danger");
          load_progress_bar.classList.add("bg-warning");
        }
        else {
          load.classList.remove("text-body");
          load.classList.remove("text-warning");
          load.classList.add("text-danger");

          load_progress_bar.classList.remove("bg-warning");
          load_progress_bar.classList.add("bg-danger");
        }
        load.innerHTML = load_value.toFixed(0) + "W";
        load_progress_bar.style.width = load_percentage * 100 + "%";

        // Update the plotly plots
        var time = new Date(device_state.time_updated * 1000);
        const systemLoadPlot = document.getElementById('system-load-plot');
        // Check if the plot has been loaded yet
        try {
          Plotly.extendTraces(systemLoadPlot, { y: [[load_value], [device_state.load_va], [pv_input_power_value]], x: [[time], [time], [time]] }, [0, 1, 2], 3600);
        } catch { }

        const chargeCurrentPlot = document.getElementById('battery-charge-current-plot');
        try {
          Plotly.extendTraces(chargeCurrentPlot, { y: [[device_state.grid_charge_current], [device_state.pv_charge_current]], x: [[time], [time]] }, [1, 2], 3600);
        } catch { }
      }

      // Battery related info
      else if (device_info.device_type == "battery") {
        // Update the battery-soc span
        const battery_soc = document.getElementById("battery-soc");
        const battery_soc_progress_bar = document.getElementById("battery-soc-progress-bar");

        var battery_percentage = device_state.state_of_charge * 100;
        if (battery_percentage < 30) {
          battery_soc.classList.remove("text-success");
          battery_soc.classList.remove("text-warning");
          battery_soc.classList.add("text-danger");

          battery_soc_progress_bar.classList.remove("bg-success");
          battery_soc_progress_bar.classList.remove("bg-warning");
          battery_soc_progress_bar.classList.add("bg-danger");
        } else if (battery_percentage < 60) {
          battery_soc.classList.remove("text-success");
          battery_soc.classList.remove("text-danger");
          battery_soc.classList.add("text-warning");

          battery_soc_progress_bar.classList.remove("bg-success");
          battery_soc_progress_bar.classList.remove("bg-danger");
          battery_soc_progress_bar.classList.add("bg-warning");
        } else {
          battery_soc.classList.remove("text-warning");
          battery_soc.classList.remove("text-danger");
          battery_soc.classList.add("text-success");

          battery_soc_progress_bar.classList.remove("bg-warning");
          battery_soc_progress_bar.classList.remove("bg-danger");
          battery_soc_progress_bar.classList.add("bg-success");
        }
        battery_soc.innerHTML = battery_percentage.toFixed(0) + "%";
        battery_soc_progress_bar.style.width = battery_percentage + "%";

        // Update the charge-current span
        const charge_current = document.getElementById("battery-charge-current");
        charge_current.innerHTML = device_state.current.toFixed(1) + "A";
        if (device_state.current < 0) {
          charge_current.classList.remove("text-success");
          charge_current.classList.add("text-warning");
        }
        else {
          charge_current.classList.remove("text-warning");
          charge_current.classList.add("text-success");
        }

        // Update the Plotly plots
        var time = new Date(device_state.time_updated * 1000);
        const batterySocPlot = document.getElementById('battery-percentage-plot');
        // Check if the plot has been loaded yet
        try {
          Plotly.extendTraces(batterySocPlot, { y: [[battery_percentage]], x: [[time]] }, [0], 3600);
        } catch { }

        const batteryVoltagePlot = document.getElementById('battery-voltage-plot');
        try {
          Plotly.extendTraces(batteryVoltagePlot, { y: [[device_state.voltage]], x: [[time]] }, [0], 3600);
        } catch { }

        const batteryCurrentPlot = document.getElementById('battery-charge-current-plot');
        try {
          Plotly.extendTraces(batteryCurrentPlot, { y: [[device_state.current]], x: [[time]] }, [0], 3600);
        } catch { }
      }
    };
  });
}