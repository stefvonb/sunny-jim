async function getData(api_server, api_port, api_endpoint, api_params = null) {
    const num_tries = 3;
    var response = null;
    var endpoint = `http://${api_server}:${api_port}/${api_endpoint}`;
    if (api_params) {
        endpoint += `?${api_params}`;
    }
    for (var i = 0; i < num_tries; i++) {
        try {
            response = await fetch(endpoint);
            if (response.ok) {
                break;
            }
            await new Promise(resolve => setTimeout(resolve, 2000));
        } catch (error) {
            console.log(error);
        }
    }

    if (response == null) {
        throw new Error(`Failed to fetch data from ${api_server}:${api_port}/${api_endpoint}?${api_params}`);
    }

    return response.json();
}

async function setUpPlots(api_server, api_port, minutes) {
    // Fetch data from the API
    const batteryData = await getData(api_server, api_port, "data/battery/past_minutes/", `minutes=${minutes}&columns=time_updated%2Cstate_of_charge%2Cvoltage%2Ccurrent`);
    const inverterData = await getData(api_server, api_port, "data/inverter/past_minutes/", `minutes=${minutes}&columns=time_updated%2Cload_power%2Cload_va%2Cpv_input_power%2Cpv_charge_current%2Cgrid_charge_current`);

    const batteryDateTimes = batteryData.time_updated.map(unix => new Date(unix * 1000));
    const inverterDateTimes = inverterData.time_updated.map(unix => new Date(unix * 1000));

    const lux_colorway = ['#007bff', '#4bbf73', '#f0ad4e', '#d9534f', '#1a1a1a'];
    const legend_style = { orientation: 'h', y: 1.1, bgcolor: 'rgba(255, 255, 255, 0.5)' };
    const margin_style = { l: 70, r: 50, b: 50, t: 50, pad: 4 };

    var plotConfig = { responsive: true };

    const systemLoadPlot = document.getElementById('system-load-plot');
    Plotly.newPlot(systemLoadPlot, [{
        x: inverterDateTimes,
        y: inverterData.load_power,
        name: 'Load Power'
    },
    {
        x: inverterDateTimes,
        y: inverterData.load_va,
        name: 'Load VA'
    },
    {
        x: inverterDateTimes,
        y: inverterData.pv_input_power,
        name: 'PV Input Power'
    }
    ], {
        xaxis: { tickformat: '%H:%M' },
        yaxis: { title: 'Power (W)' },
        margin: margin_style,
        legend: legend_style,
        colorway: lux_colorway,
        showlegend: true
    }, plotConfig);

    const batteryPercentagePlot = document.getElementById('battery-percentage-plot');
    Plotly.newPlot(batteryPercentagePlot, [{
        x: batteryDateTimes,
        y: batteryData.state_of_charge.map(function (x) { return x * 100; }),
        name: 'State of Charge'
    }], {
        xaxis: { tickformat: '%H:%M' },
        yaxis: { title: 'State of Charge (%)' },
        margin: margin_style,
        legend: legend_style,
        colorway: lux_colorway,
        showlegend: true
    }, plotConfig);

    const batteryChargeCurrentPlot = document.getElementById('battery-charge-current-plot');
    Plotly.newPlot(batteryChargeCurrentPlot, [{
        x: batteryDateTimes,
        y: batteryData.current,
        name: 'Battery Current'
    },
    {
        x: inverterDateTimes,
        y: inverterData.grid_charge_current,
        name: 'Grid Charge Current'
    },
    {
        x: inverterDateTimes,
        y: inverterData.pv_charge_current,
        name: 'PV Charge Current'
    }], {
        xaxis: { tickformat: '%H:%M' },
        yaxis: { title: 'Current (A)' },
        margin: margin_style,
        legend: legend_style,
        colorway: lux_colorway,
        showlegend: true
    }, plotConfig);

    const batteryVoltagePlot = document.getElementById('battery-voltage-plot');
    Plotly.newPlot(batteryVoltagePlot, [{
        x: batteryDateTimes,
        y: batteryData.voltage,
        name: 'Battery Voltage'
    }], {
        xaxis: { tickformat: '%H:%M' },
        yaxis: { title: 'Voltage (V)' },
        margin: margin_style,
        legend: legend_style,
        colorway: lux_colorway,
        showlegend: true
    }, plotConfig);
}

async function setUpElements(api_server, api_port) {
    const currentInverterData = await getData(api_server, api_port, "devices/inverter/");
    
    if (currentInverterData.device_state.grid_state == 'off') {
        const timeLastOn = await getData(api_server, api_port, "data/time_when_grid_last_on/")
        const timeLastOnDate = new Date(timeLastOn.time_grid_last_on * 1000);
        const timeLastOnTime = timeLastOnDate.getHours().toString().padStart(2, '0') + ':' + timeLastOnDate.getMinutes().toString().padStart(2, '0');

        document.getElementById('grid-off-since').innerHTML = `(since ${timeLastOnTime})`;
    }
}