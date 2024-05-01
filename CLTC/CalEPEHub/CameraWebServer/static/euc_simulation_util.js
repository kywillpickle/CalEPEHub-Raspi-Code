/* Created by Kyle Pickle for use with the CLTC's CalEPEHub project */

var canvas, ind_canvas, ctx, ind_ctx,
    occ_status, num_trials, width, height, pattern, step
    simulation_running = false, stop_cmd = false

$(document).ready(function() {
    canvas = document.getElementById('disp-canvas')
    ind_canvas = document.getElementById('ind-canvas')
    ctx = canvas.getContext('2d')
    ind_ctx = ind_canvas.getContext('2d')
    ctx.translate(canvas.width/2, canvas.height/2)
    ind_ctx.translate(canvas.width/2, canvas.height/2)
});

function moveIndicator(x, y) {
    ind_ctx.clearRect(-canvas.width/2, -canvas.height/2, canvas.width, canvas.height)
    ind_ctx.beginPath();
    ind_ctx.moveTo((canvas.width/Math.max(width, height))*(-0.8+2*x)/2,
                   (canvas.height/Math.max(width, height))*(-0.8+2*y)/2);
    ind_ctx.lineTo((canvas.width/Math.max(width, height))*(0.8+2*x)/2,
                   (canvas.height/Math.max(width, height))*(0.8+2*y)/2);
    ind_ctx.lineWidth = 1;
    ind_ctx.stroke();
    ind_ctx.beginPath();
    ind_ctx.moveTo((canvas.width/Math.max(width, height))*(0.8+2*x)/2,
                   (canvas.height/Math.max(width, height))*(-0.8+2*y)/2);
    ind_ctx.lineTo((canvas.width/Math.max(width, height))*(-0.8+2*x)/2,
                   (canvas.height/Math.max(width, height))*(0.8+2*y)/2);
    ind_ctx.lineWidth = 1;
    ind_ctx.stroke();
}

function drawSquare(x, y) {
    ctx.fillRect(
        (canvas.width/Math.max(width, height))*(-1+2*x)/2+1,
        (canvas.height/Math.max(width, height))*(-1+2*y)/2+1,
        canvas.width/Math.max(width, height)-2,
        canvas.height/Math.max(width, height)-2
    )
}

async function testSquare(x, y) {
    occ_detected = false
    moveIndicator(x, y)
    for(var i = 0; i < step*10; ++i) {
        occ_detected = occ_detected || (occ_status === 'Occupied')
        await new Promise(resolve => setTimeout(resolve, 50))
        if(stop_cmd) return
    }
    if (occ_detected) drawSquare(x, y)
}

function gatherInputs() {
    width = document.getElementById('input-grid-width').value
    if(width === '') width = 19
    else width = Number(width)
    height = document.getElementById('input-grid-height').value
    if(height === '') height = 19
    else height = Number(height)
    num_trials = document.getElementById('input-num-trials').value
    if(num_trials === '') num_trials = 1
    else num_trials = Number(num_trials)
    pattern = document.getElementById('input-pattern').value
    step = document.getElementById('input-step').value
    if(step === '') step = 5
    else step = Number(step)
}

async function runSimulation() {
    stop_cmd = true
    while(simulation_running) {
        await new Promise(resolve => setTimeout(resolve, 100));
    }
    simulation_running = true
    stop_cmd = false
    ctx.clearRect(-canvas.width/2, -canvas.height/2, canvas.width, canvas.height)
    /* Gather input values */
    gatherInputs()

    /* Draw each trial */
    if(pattern === 'up-and-down') {
        for(var n = 0; n < num_trials; n++) {
            for(var x = -Math.floor(width/2); x <= Math.floor(width/2); ++x) {
                for(var y = -Math.floor(height/2); y <= Math.floor(height/2)-1; ++y) {
                    ctx.fillStyle = `rgba(
                        ${255},
                        ${0},
                        ${0},
                        ${(1 - (1 - 1/num_trials/2) * (1 - 1/num_trials/2))}
                    )`;
                    await testSquare(x, y)
                    if(stop_cmd) {simulation_running = false; return}
                }
                for(var y = Math.floor(height/2); y >= -Math.floor(height/2); --y) {
                    if(y === Math.floor(height/2)) {
                        ctx.fillStyle = `rgba(
                            ${255},
                            ${0},
                            ${0},
                            ${(1 - (1 - 1/num_trials) * (1 - 1/num_trials))}
                        )`;
                    } else {
                        ctx.fillStyle = `rgba(
                            ${255},
                            ${0},
                            ${0},
                            ${(1 - (1 - 1/num_trials/2) * (1 - 1/num_trials/2))}
                        )`;
                    }
                    await testSquare(x, y)
                    if(stop_cmd) {simulation_running = false; return}
                }
            }
        }
    }
    else if(pattern === 'alternate') {
        for(var n = 0; n < num_trials; n++) {
            for(var x = -Math.floor(width/2); x <= Math.floor(width/2); ++x) {
                if(x % 2 === 0) {
                    for(var y = -Math.floor(height/2); y <= Math.floor(height/2); ++y) {
                        await testSquare(x, y)
                        if(stop_cmd) {simulation_running = false; return}
                    }
                } else {
                    for(var y = Math.floor(height/2); y >= -Math.floor(height/2); --y) {
                        await testSquare(x, y)
                        if(stop_cmd) {simulation_running = false; return}
                    }
                }
            }
        }
    }
    ind_ctx.clearRect(-canvas.width/2, -canvas.height/2, canvas.width, canvas.height)
    simulation_running = false;
}

function updateStatusLoop() {
    // Fetch status information
    var statusPromise = fetch('/camera_status')
    .then(response => response.json())
    .then(data => occ_status = data.status)
    .catch(error => console.error('Error fetching status:', error));
    var timeOutPromise = new Promise(function(resolve, reject) {
        setTimeout(resolve, 500, 'Timeout Done')
      })
  
      Promise.all(
      [statusPromise, timeOutPromise]).then(function(values) {
        document.getElementById('occ-disp').textContent = occ_status
        if(occ_status === 'Occupied') document.getElementById('occ-disp').style.backgroundColor = `rgb(40, 255, 40)`
        else document.getElementById('occ-disp').style.backgroundColor = 'white'
        //Repeat
        updateStatusLoop()
      })
}

function postStartTest() {
    gatherInputs()
    fetch('http://camera-calepehub.local:5000/start_test', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            grid_size:  [width, height],
            step_time:  step,
            num_trials: num_trials,
            pattern:    pattern
        }),
    })
    .then(response => response.json())
    .then(data => console.log(data.message))
    .catch((error) => console.error('Error:', error));
}

updateStatusLoop()