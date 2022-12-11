import {BACKGROUND, DEAD, FISH_COLORMAP, FISH_IMAGE_SIZE} from "./fishConfig.js";

class Particle {
    constructor(x, y, fish, statusCode, responseTime) {
        this.statusCode = statusCode
        this.fish = fish;
        if (this.statusCode == 500) {
            this.fish = DEAD + fish;
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
        this.colorMap = FISH_IMAGE_SIZE
    }

    tick(duration) {
        this.x += -1 * this.vx * duration;
        this.y += this.vy * duration;
    }

    draw(context, imageCache) {
        const id = `${this.fish}`
        const img = imageCache.getImages().find(i => i.name === id);
        if(img) {
            context.drawImage(img.img, this.x, this.y, this.colorMap[id].w, this.colorMap[id].h);
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
        this.colorMap = FISH_COLORMAP
        this.bottomOffset = 100

    }

    addFish(fish, statusCode) {
        var stats = this.nextBarInfo.get(fish)
        if (stats == null) {
            stats = {
                total: 0,
                200: 0,
                500: 0
            }
        }
        stats.total = stats.total + 1
        stats[statusCode] = stats[statusCode] + 1
        this.nextBarInfo.set(fish, stats);
    }

    tick(duration) {
        this.sinceLastBar += duration;
        if (this.sinceLastBar > 3) {
            this.sinceLastBar = 0;
            const total = Array.from(this.nextBarInfo.values(), x => x.total).reduce(function(first, second) {
                return first + second;
            }, 0);
            if (total > 0) {
                const nextBar = Array.from(this.nextBarInfo.entries()).map(function([fish, count]) {
                    return {
                        fish,
                        percentage: count.total / total,
                        200:  count[200] / total,
                        500:  count[500] / total,
                    };
                }.bind(this)).sort(function(first, second) {
                    return first.fish.localeCompare(second.fish);
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
            this.roundRect(context, 'rgba(225,225,225,0.2)', x, this.app.canvas.height - this.bottomOffset - totalHeight, width, totalHeight, 8)
            context.fillStyle ="";

            bar.forEach((function(part) {
                if (part[500] > 0) {
                    let fish = part.fish;
                    fish = DEAD + fish;
                    const partHeight = height * part[500];
                    this.roundRect(context, this.colorMap[fish], x, this.app.canvas.height - this.bottomOffset - (partHeight + offset), width, partHeight, 8)

                    offset += partHeight;
                }
                const partHeight = height * part[200];
                this.roundRect(context, this.colorMap[part.fish], x, this.app.canvas.height - this.bottomOffset - (partHeight + offset), width, partHeight, 8)
                offset += partHeight;
            }).bind(this));
        }).bind(this));
    }
}

let ParticleMaxSize=200
let NumaImageSize=100

export class App {
    constructor(canvas) {
        this.canvas = canvas;
        this.particles = [];
        this.chart = new Chart(this, canvas);
        this.sliders = new Sliders(this)
    }

    addParticle() {
        var sendTime = (new Date()).getTime();
        fetch('./fish', {
            method: "POST",
            keepalive: false,
            body: JSON.stringify(this.sliders.GetValues()),
        })
        .then(function(res) {
           return res.json().then(fish => ({ fish, res }))
        }).then((function(res) {
            res.fishImg = `${res.fish}${Math.floor(Math.random() * 4)}`
            let receiveTime = (new Date()).getTime();
            let responseTimeMs = receiveTime - sendTime;
            let startingY = (this.canvas.height - this.chart.height - ParticleMaxSize - NumaImageSize) * Math.random() + NumaImageSize
            this.particles.unshift(new Particle(this.canvas.width, startingY, res.fishImg, res.res.status, responseTimeMs));
            this.particles = this.particles.slice(0, 200);
            // disabling the chart
            // this.chart.addFish(res.fish, res.res.status);
            this.sliders.addFish(res.fish)
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

            const img = imageCache.getImages().find(i => i.name === BACKGROUND);
            context.drawImage(img.img, 0, 0, this.canvas.width, this.canvas.height);

            this.getObjects().forEach((obj) => obj.draw(context, imageCache));
        }.bind(this);

        setInterval(draw, 10);
        setInterval(this.addParticle.bind(this), 300);
        draw();
    }
}

export class Fish {
    constructor(fish) {
        this.fish = fish;
        this.isSelected = false;

        const reload = () => {
            const request = new XMLHttpRequest();
            request.open('GET', './env.js' + '?nocache=' + (new Date()).getTime(), false);  // `false` makes the request synchronous
            request.send(null);

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
        }

        reload();

        this.colorMap = FISH_COLORMAP

        this.square = document.createElement('div');
        this.square.className = "version-block"
        this.checkBox = document.createElement('input');
        this.checkBox.type = "checkbox"
        this.checkBox.className = "checkbox-style"
        this.checkBox.name = fish
        this.checkBox.value = fish
        const circle = document.createElement('div');
        const text = document.createElement('span');
        text.innerText = fish
        text.className = "version-style"
        circle.className = "square " + fish;
        circle.style["background"] = this.colorMap[fish];
        circle.shadowBlur=0;
        this.square.appendChild(this.checkBox)
        // this.square.appendChild(circle)
        this.square.appendChild(text)
    }
    setIsSelected(isSelected) {
        this.isSelected = isSelected
        if (isSelected) {
            this.checkBox.checked = true
        } else {
            this.checkBox.checked = false
        }
    }

    setSliderValues(updatedValues) {
        this.return500 = updatedValues;
        this.delayPercent = updatedValues;
        this.delayLength = 0;
    }

    GetSliderValues() {
        return {
            "fish": this.fish,
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
        this.return500.addEventListener("input", this.updateFish.bind(this))
    
        this.delayPercent = document.getElementById("delayPercent");
        this.delayPercentText = document.getElementById("delayPercentText");
        this.delayPercent.addEventListener("input", this.updateFish.bind(this))
        
        this.delayLength = document.getElementById("delayLength");
        this.delayLengthText = document.getElementById("delayLengthText");
        this.delayLength.addEventListener("input", this.updateFish.bind(this))

        
        
        //TODO: cycle through fishSwitcher instead of having seperate storage
        this.availableFishes = []
        this.fishSwitcher = document.getElementById("availableFishes")
        this.currentFishLabel = document.getElementById("currentFish");
        this.currentFish = null

    }

    updateFish() {
        this.currentFish.return500 = this.return500.value;
        this.currentFish.delayPercent =this.delayPercent.value;
        this.currentFish.delayLength =  this.delayLength.value;
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
    addFish(fish) {
        let isNewFish = true
        this.availableFishes.forEach((storedFish)=> {
            if (fish == storedFish.fish) {
                isNewFish = false
            }
        })
        if (!isNewFish) {
            return
        }
 
        let newFish = new Fish(fish)

        let isSelected = false
        if (this.currentFish == null) {
            this.currentFish = newFish
            this.currentFishLabel.innerText = capitalize(newFish.fish)
            isSelected = true
            this.SetSliders(newFish)
        }
        newFish.setIsSelected(isSelected)

        newFish.square.addEventListener("click", this.setCurrentFish(newFish).bind(this))
        this.availableFishes.push(newFish)
        this.fishSwitcher.appendChild(newFish.square)
    }
    
    setCurrentFish(newFish) {
        return function() {
            this.currentFish.setIsSelected(false)
            this.currentFish = newFish
            this.currentFishLabel.innerText = capitalize(newFish.fish)
            this.currentFish.setIsSelected(true)
            this.SetSliders(newFish)
        }.bind(this)
    }

    SetSliders(fish) {
        this.return500.value = fish.return500
        this.return500Text.innerText = fish.return500 + "%"
        this.delayPercent.value = fish.delayPercent
        this.delayPercentText.innerText = fish.delayPercent + "%"
        this.delayLengthText.innerText = fish.delayLength + "s"
        this.delayLength.value = fish.delayLength
    }

    GetValues() {
        if (this.availableFishes.length == 0) {
            return "[]"
        }
        var values = []
        this.availableFishes.forEach((fish)=> {
            values.push(fish.GetSliderValues())
        })
        return values
    }
}