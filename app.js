class Particle {
    constructor(x, y, color, statusCode, responseTime) {
        this.statusCode = statusCode
        this.color = color;
        if (this.statusCode == 500) {
            this.color = "dark" + color;
        }
        this.x = x;
        this.y = y;

        this.size = Math.random() * 20 + 10;
        this.maxSpeeed = 300
        this.maxSlowDown = 200
        this.maxDelay = 5000
        this.vx = this.maxSpeeed - (this.maxSlowDown * responseTime/this.maxDelay)
        if (responseTime > this.maxDelay) {
            this.vx = this.maxSpeeed - this.maxSlowDown
        }

        this.vy = 0;
        this.colorMap = {
            background: { w: 70, h: 70},
            yellow0: { w: 122, h: 70},
            blue0: { w: 73, h: 70},
            darkblue0: { w: 73, h: 70},
            darkyellow0: { w: 122, h: 70},
            yellow1: { w: 105, h: 61},
            yellow2:{ w: 91, h: 56},
            blue1: { w: 62, h: 60},
            blue2: { w: 52, h: 50},
            darkblue1: { w: 62, h: 60},
            darkblue2:{ w: 52, h: 50},
            darkyellow1: { w: 105, h: 61},
            darkyellow2: { w: 91, h: 56},
        }
    }

    tick(duration) {
        this.x += -1 * this.vx * duration;
        this.y += this.vy * duration;
    }

    draw(context, imageCache) {
        // const img = document.createElement("img");
        const id = `${this.color}`
        const img = imageCache.getImages().find(i => i.name === id);
        // img.src = this.colorMap[this.color]
        if(img) {
            context.drawImage(img.img, this.x, this.y, this.colorMap[id].w, this.colorMap[id].h);
            if (this.statusCode == 500) {
                // context.lineWidth = 5;
                // context.strokeStyle = "black";
                // context.stroke();
            }
        }
    }
}

class Chart {
    constructor(app, canvas) {
        this.app = app;
        this.canvas = canvas
        this.sinceLastBar = 0;
        this.bars = [];
        this.nextBarInfo = new Map();
        this.height = 180
        this.width = 17;
        this.colorMap = {
            "blue": "#FEB202", //"#7719D6",
            "darkyellow" : "#FF0000",
            "yellow" : "#FEB202",
            "darkblue" : "#FF0000",
        }
        this.bottomOffset = 100

    }

    addColor(color, statusCode) {
        var stats = this.nextBarInfo.get(color)
        if (stats == null) {
            stats = {
                total: 0,
                200: 0,
                500: 0
            }
        }
        stats.total = stats.total + 1
        stats[statusCode] = stats[statusCode] + 1
        this.nextBarInfo.set(color, stats);
    }

    tick(duration) {
        this.sinceLastBar += duration;
        if (this.sinceLastBar > 3) {
            this.sinceLastBar = 0;
            const total = Array.from(this.nextBarInfo.values(), x => x.total).reduce(function(first, second) {
                return first + second;
            }, 0);
            if (total > 0) {
                const nextBar = Array.from(this.nextBarInfo.entries()).map(function([color, count]) {
                    return {
                        color,
                        percentage: count.total / total,
                        200:  count[200] / total,
                        500:  count[500] / total,
                    };
                }.bind(this)).sort(function(first, second) {
                    return first.color.localeCompare(second.color);
                });
                this.bars.push(nextBar);
                if (this.bars.length > 600) {
                    this.bars.shift();
                }
            }
            this.nextBarInfo = new Map();
        }
    }

    roundRect(ctx, color, x, y, width, height, radius) {
        /*
         * Draws a rounded rectangle using the current state of the canvas.
         */
        // ctx.stroke()
        ctx.fill();
        ctx.beginPath();
        ctx.fillStyle = color;
        if (width < 2 * radius) radius = width / 2;
        if (height < 2 * radius) radius = height / 2;
        ctx.moveTo(x + radius, y);
        ctx.arcTo(x + width, y, x + width, y + height, radius);
        ctx.arcTo(x + width, y + height, x, y + height, radius);
        ctx.arcTo(x, y + height, x, y, radius);
        ctx.arcTo(x, y, x + width, y, radius);
        ctx.closePath();
    }

    draw(context) {
        context.shadowBlur=0;
        context.shadowColor='none';
        const height = this.height;
        const width = this.width;
        const distance = 20;
        const count = this.app.canvas.width / (3 * (width + distance));
        const start = Math.max(0, this.bars.length - count);
        const canvasWidth = this.canvas.width
        this.bars.slice(start).reverse().forEach((function(bar, i) {
            let offset = 0;
            const x = canvasWidth/3 - (distance * i + width * i)

            const totalHeight = height + 20;
            // // context.fillRect(x, this.app.canvas.height - 20 - (partHeight + offset), -width, partHeight);
            this.roundRect(context, 'rgba(225,225,225,0.2)', x, this.app.canvas.height - this.bottomOffset - totalHeight, width, totalHeight, 8)
            context.fillStyle ="";

            bar.forEach((function(part) {
                if (part[500] > 0) {
                    let color = part.color;
                    color = "dark" + color;
                    const partHeight = height * part[500];
                    // context.fillRect(x, this.app.canvas.height - 20 - (partHeight + offset), -width, partHeight);
                    // console.log(color, context.fillStyle, x,this.app.canvas.height - this.bottomOffset - (partHeight + offset), width, partHeight )
                    this.roundRect(context, this.colorMap[color], x, this.app.canvas.height - this.bottomOffset - (partHeight + offset), width, partHeight, 8)

                    offset += partHeight;
                }
                // context.fillStyle =this.colorMap[part.color];
                const partHeight = height * part[200];
                // console.log(part.color,context.fillStyle, x,this.app.canvas.height - this.bottomOffset - (partHeight + offset), width, partHeight )
                // context.fillRect(x, this.app.canvas.height - 20 - (partHeight + offset), -width, partHeight);
                this.roundRect(context, this.colorMap[part.color], x, this.app.canvas.height - this.bottomOffset - (partHeight + offset), width, partHeight, 8)
                offset += partHeight;
            }).bind(this));
        }).bind(this));
    }
}

let ParticleMaxSize=200
let ArgoImageSize=100

export class App {
    constructor(canvas) {
        this.canvas = canvas;
        this.particles = [];
        this.chart = new Chart(this, canvas);
        this.sliders = new Sliders(this)
    }

    // http://localhost:8080 to test
    addParticle() {
        var sendTime = (new Date()).getTime();
        fetch('./color', {
            method: "POST",
            keepalive: false,
            body: JSON.stringify(this.sliders.GetValues()),
        })
        .then(function(res) {
           return res.json().then(color => ({ color, res }))
        }).then((function(res) {
            res.colorImg = `${res.color}${Math.floor(Math.random() * 4)}`
            var receiveTime = (new Date()).getTime();
            var responseTimeMs = receiveTime - sendTime;
            let startingY = (this.canvas.height - this.chart.height - ParticleMaxSize - ArgoImageSize) * Math.random() + ArgoImageSize
            this.particles.unshift(new Particle(this.canvas.width, startingY, res.colorImg, res.res.status, responseTimeMs));
            this.particles = this.particles.slice(0, 200);
            this.chart.addColor(res.color, res.res.status);
            this.sliders.addColor(res.color)
        }).bind(this));
    }

    getObjects() {
        return [...this.particles, this.chart];
    }

    run(imageCache) {
        const context = this.canvas.getContext('2d');
        let prevDate = new Date();

        const draw = function() {
            const nextPrevDate = new Date();
            const duration = (nextPrevDate.getTime() - prevDate.getTime()) / 1000;
            this.getObjects().forEach((obj) => obj.tick && obj.tick(duration));
            prevDate = nextPrevDate;

            const img = imageCache.getImages().find(i => i.name === 'background');
            // const img = document.createElement("img");
            // img.src = "background.png"
            // context.fillStyle = 'rgba(39,12,83,0.5)';
            // context.fillRect(0, 0, this.canvas.width, this.canvas.height);
            context.drawImage(img.img, 0, 0, this.canvas.width, this.canvas.height);

            this.getObjects().forEach((obj) => obj.draw(context, imageCache));
        }.bind(this);

        setInterval(draw, 10);
        setInterval(this.addParticle.bind(this), 300);
        draw();
    }
}

export class Color {
    constructor(color) {
        this.color = color;
        this.isSelected = false;

        const reload = () => {
            console.log("calling reload")
            // http://localhost:8080 to test
            const request = new XMLHttpRequest();
            request.open('GET', './env.js' + '?nocache=' + (new Date()).getTime(), false);  // `false` makes the request synchronous
            request.send(null);

            document.getElementById('version-list').style.display = 'none';
            document.getElementById('params-tuning').style.display = 'none';

            if (request.status === 200) {
                const str = request.responseText
                const jsonObj = JSON.parse(str.replace(new RegExp(/const ENV_.*?=/), ''))
                this.return500 = jsonObj.errorRate ? jsonObj.errorRate : 0;
                this.delayPercent = 100;
                this.delayLength = jsonObj.latency ? jsonObj.latency : 0;
            } else {
                this.return500 = 0
                this.delayPercent = 0
                this.delayLength = 0
            }
            // console.log(this.return500)
        }

        // setInterval(reload, 500);
        reload();

        this.colorMap = {
            "blue": "#FEB202", //"#7719D6",
            "darkyellow" : "#FF0000",
            "yellow" : "#FEB202",
            "darkblue" : "#FF0000",
        }

        this.square = document.createElement('div');
        this.square.className = "version-block"
        this.checkBox = document.createElement('input');
        this.checkBox.type = "checkbox"
        this.checkBox.className = "checkbox-style"
        this.checkBox.name = color
        this.checkBox.value = color
        const circle = document.createElement('div');
        const text = document.createElement('span');
        text.innerText = "Version"
        text.className = "version-style"
        circle.className = "square " + color;
        circle.style["background"] = this.colorMap[color];
        circle.shadowBlur=0;
        this.square.appendChild(this.checkBox)
        this.square.appendChild(circle)
        this.square.appendChild(text)
    }
    setIsSelected(isSelected) {
        this.isSelected = isSelected
        if (isSelected) {
            this.checkBox.checked = true
            // this.square.style["borderStyle"] = "solid";
        } else {
            this.checkBox.checked = false
            // this.square.style["borderStyle"] = "hidden";
        }
    }

    setSliderValues(updatedValues) {
        this.return500 = updatedValues;
        this.delayPercent = updatedValues;
        this.delayLength = 0;
    }

    GetSliderValues() {
        return {
            "color": this.color,
            "return500": parseInt(this.return500),
            "delayPercent": parseInt(this.delayPercent),
            "delayLength": parseInt(this.delayLength) // parseInt(this.delayPercent) > 0 ? 1 : 0 // parseInt(this.delayLength)
        }
    }
}

const capitalize = (s) => {
    if (typeof s !== 'string') return ''
    return s.charAt(0).toUpperCase() + s.slice(1)
  }

export class Sliders {
    constructor(app) {
        this.app = app;

        this.return500 = document.getElementById("return500");
        this.return500Text = document.getElementById("output500");
        this.return500.addEventListener("input", this.updateColor.bind(this))
    
        this.delayPercent = document.getElementById("delayPercent");
        this.delayPercentText = document.getElementById("delayPercentText");
        this.delayPercent.addEventListener("input", this.updateColor.bind(this))
        
        this.delayLength = document.getElementById("delayLength");
        this.delayLengthText = document.getElementById("delayLengthText");
        this.delayLength.addEventListener("input", this.updateColor.bind(this))

        
        
        //TODO: cycle through colorSwitcher instead of having seperate storage
        this.availableColors = []
        this.colorSwitcher = document.getElementById("availableColors")
        this.currentColorLabel = document.getElementById("currentColor");
        this.currentColor = null

    }

    updateColor() {
        this.currentColor.return500 = this.return500.value;
        this.currentColor.delayPercent =this.delayPercent.value;
        this.currentColor.delayLength =  this.delayLength.value //this.currentColor.delayPercent > 0 ? 1: 0 //this.delayLength.value;
    }

    draw(context) {
        context.shadowBlur=0;
        context.shadowColor='none';
        const height = 600;
        const width = 300;
        const xoffset = 50;
        const yoffset = 50;

        const xStart = this.app.canvas.width - width - xoffset;
        context.fillRect(xStart, yoffset, xStart + width, height + yoffset);
    }
    addColor(color) {
        newColor = true
        this.availableColors.forEach((storedColor)=> {
            if (color == storedColor.color) {
                newColor = false
            }
        })
        if (!newColor) {
            return
        }
 
        var newColor = new Color(color)

        var isSelected = false
        if (this.currentColor == null) {
            this.currentColor = newColor
            this.currentColorLabel.innerText = capitalize(newColor.color)
            isSelected = true
            this.SetSliders(newColor)
        }
        newColor.setIsSelected(isSelected)

        newColor.square.addEventListener("click", this.setCurrentColor(newColor).bind(this))
        // console.log('newColor', newColor)
        this.availableColors.push(newColor)
        this.colorSwitcher.appendChild(newColor.square)

        // console.log([...this.availableColors.entries()])

    }
    
    setCurrentColor(newColor) {
        return function() {
            this.currentColor.setIsSelected(false)
            this.currentColor = newColor
            this.currentColorLabel.innerText = capitalize(newColor.color)
            this.currentColor.setIsSelected(true)
            this.SetSliders(newColor)
        }.bind(this)
    }

    SetSliders(color) {
        this.return500.value = color.return500
        this.return500Text.innerText = color.return500 + "%"
        this.delayPercent.value = color.delayPercent
        this.delayPercentText.innerText = color.delayPercent + "%"
        this.delayLengthText.innerText = color.delayLength + "s"
        this.delayLength.value = color.delayLength // delayPercent > 0 ? 1: 0 // color.delayLength
    }

    GetValues() {
        if (this.availableColors.length == 0) {
            return "[]"
        }
        var values = []
        this.availableColors.forEach((color)=> {
            values.push(color.GetSliderValues())
        })
        return values
    }
}