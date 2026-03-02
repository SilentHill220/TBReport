// ===== PARTICLE SYSTEM =====
function initParticles() {
    const canvas = document.getElementById('particleCanvas');
    if (!canvas) return; // Guard clause

    const ctx = canvas.getContext('2d');
    const hero = document.getElementById('portalHero');
    const glow = document.getElementById('portalGlow');

    if (!hero) return;

    let particles = [];
    let mouseX = 0, mouseY = 0;
    let targetX = 0, targetY = 0;

    function resize() {
        canvas.width = hero.offsetWidth;
        canvas.height = hero.offsetHeight;
    }
    resize();
    window.addEventListener('resize', resize);

    // Create particles
    class Particle {
        constructor() {
            this.reset();
        }
        reset() {
            this.x = Math.random() * canvas.width;
            this.y = Math.random() * canvas.height;
            this.size = Math.random() * 3 + 1;
            this.speedX = (Math.random() - 0.5) * 0.5;
            this.speedY = (Math.random() - 0.5) * 0.5;
            this.opacity = Math.random() * 0.5 + 0.2;
            this.color = Math.random() > 0.5 ?
                `rgba(32, 194, 132, ${this.opacity})` :
                `rgba(0, 212, 255, ${this.opacity})`;
        }
        update() {
            // Attract to mouse
            const dx = targetX - this.x;
            const dy = targetY - this.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < 150) {
                this.x += dx * 0.01;
                this.y += dy * 0.01;
            }

            this.x += this.speedX;
            this.y += this.speedY;

            if (this.x < 0 || this.x > canvas.width) this.speedX *= -1;
            if (this.y < 0 || this.y > canvas.height) this.speedY *= -1;
        }
        draw() {
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
            ctx.fillStyle = this.color;
            ctx.fill();
        }
    }

    for (let i = 0; i < 60; i++) {
        particles.push(new Particle());
    }

    // Mouse tracking
    hero.addEventListener('mousemove', (e) => {
        const rect = hero.getBoundingClientRect();
        mouseX = e.clientX - rect.left;
        mouseY = e.clientY - rect.top;

        // CSS glow disabled - shader handles lighting now
        // if (glow) {
        //     glow.style.left = mouseX + 'px';
        //     glow.style.top = mouseY + 'px';
        // }
    });

    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Smooth mouse follow
        targetX += (mouseX - targetX) * 0.05;
        targetY += (mouseY - targetY) * 0.05;

        // Draw connections
        particles.forEach((p, i) => {
            particles.slice(i + 1).forEach(p2 => {
                const dx = p.x - p2.x;
                const dy = p.y - p2.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 80) {
                    ctx.beginPath();
                    ctx.moveTo(p.x, p.y);
                    ctx.lineTo(p2.x, p2.y);
                    ctx.strokeStyle = `rgba(32, 194, 132, ${0.15 * (1 - dist / 80)})`;
                    ctx.stroke();
                }
            });
        });

        particles.forEach(p => {
            p.update();
            p.draw();
        });

        requestAnimationFrame(animate);
    }
    animate();
}

// ===== WEBGL SHADER EFFECT WITH DEPTH MAP =====
async function initHeroShader() {
    console.log("initHeroShader called");
    const container = document.getElementById('heroShaderContainer');
    if (!container || typeof PIXI === 'undefined') {
        console.log('PixiJS or container not available', { container, pixi: typeof PIXI });
        return;
    }
    console.log("Container found, PIXI available");

    try {
        console.log("Creating PIXI Application");
        const app = new PIXI.Application({
            resizeTo: container,
            backgroundColor: 0x0a0e14,
            backgroundAlpha: 1
        });
        container.appendChild(app.view);
        app.view.style.position = 'absolute';
        app.view.style.inset = '0';
        app.view.style.borderRadius = '24px';
        console.log("PIXI App created and appended");

        // Try to load depth map images
        let bgTex, depthTex;
        let useDepthMap = false;

        try {
            console.log("Attempting to load assets...");
            bgTex = await PIXI.Assets.load('/static/images/launch_bg.jpg');
            console.log("Background loaded", bgTex);
            depthTex = await PIXI.Assets.load('/static/images/depth.jpg');
            console.log("Depth map loaded", depthTex);
            useDepthMap = true;
            console.log('Depth map loaded successfully');
        } catch (e) {
            console.log('Asset loading failed, using procedural shader:', e);
        }

        if (useDepthMap) {
            // === DEPTH MAP PARALLAX SHADER ===
            const bgSprite = new PIXI.Sprite(bgTex);

            const fragSrc = `
                precision mediump float;
                varying vec2 vTextureCoord;
                uniform sampler2D uSampler;
                uniform sampler2D uDepthMap;
                uniform float uTime;
                uniform vec2 uMouse;
                uniform vec2 uResolution;
                
                // Ported from Unity Shader "Custom/DepthParallax_Devouring_Liquid"
                const vec3 FOG_COLOR = vec3(0.05, 0.0, 0.1); 
                const vec3 EDGE_COLOR = vec3(0.2, 0.0, 0.4);
                const vec3 GLOW_TARGET_COLOR = vec3(1.0, 1.0, 0.0);
                
                // Settings
                const float BREATH_SPEED = 1.0;
                const float BREATH_AMP = 0.005; // Less distortion
                const float DISTORT_STRENGTH = 0.01;
                const float DISTORT_SPEED = 0.5;
                const float DISTORT_FREQ = 3.0;
                const float PARALLAX_STRENGTH = 0.01;
                const float LIQUID_FREQ = 15.0;
                const float LIQUID_SPEED = 1.0;
                const float LIQUID_AMP = 0.03;
                const float DEVOUR_PROGRESS = -0.3; // Very negative to start super clear
                const float EDGE_SOFTNESS = 0.1; 

                float liquidNoise(vec2 uv, float time) {
                    float wave1 = sin(uv.x * LIQUID_FREQ + time * 0.5);
                    float wave2 = sin((uv.y + uv.x) * (LIQUID_FREQ * 0.8) - time * 1.2);
                    float wave3 = cos(uv.y * (LIQUID_FREQ * 1.5) + time);
                    return (wave1 + wave2 + wave3) * 0.33;
                }

                void main() {
                    vec2 uv = vTextureCoord;
                    
                    // 1. Base Depth & Distortion
                    float baseDepth = texture2D(uDepthMap, uv).r;
                    
                    // Twist/Distortion
                    vec2 uvToCenter = uv - 0.5;
                    float distToCenter = length(uvToCenter);
                    vec2 distortOffset = vec2(0.0);
                    
                    // Only distort if depth is far (background), stabilize foreground
                    if(baseDepth < 0.9) {
                        float twistTime = uTime * DISTORT_SPEED;
                        float radialWave = sin(distToCenter * DISTORT_FREQ - twistTime);
                        distortOffset = normalize(uvToCenter) * radialWave * DISTORT_STRENGTH * (1.0 - baseDepth);
                    }
                    vec2 distortedUV = uv + distortOffset;
                    
                    // Breathing Zoom
                    float breathCycle = sin(uTime * BREATH_SPEED);
                    float currentScale = 1.0 - (breathCycle * BREATH_AMP * baseDepth);
                    vec2 zoomedUV = (distortedUV - 0.5) * currentScale + 0.5;
                    
                    // Parallax
                    vec2 inputOffset = clamp(uMouse * 1.5, -1.0, 1.0); 
                    vec2 parallaxOffset = (baseDepth - 0.5) * PARALLAX_STRENGTH * inputOffset;
                    vec2 finalUV = zoomedUV + parallaxOffset;
                    
                    // Safety Clamp
                    finalUV = clamp(finalUV, 0.002, 0.998);
                    
                    // 2. Sample Texture
                    vec4 col = texture2D(uSampler, finalUV);
                    float finalDepth = texture2D(uDepthMap, finalUV).r;
                    
                    // 3. Liquid Devouring Logic
                    float time = uTime * LIQUID_SPEED;
                    float noiseVal = liquidNoise(finalUV, time);
                    
                    float dynamicThreshold = DEVOUR_PROGRESS + noiseVal * LIQUID_AMP;
                    
                    // Masking 
                    float mainMask = 1.0 - smoothstep(dynamicThreshold - EDGE_SOFTNESS, dynamicThreshold, finalDepth);
                    
                    // Edge Highlight
                    float edgeMask = smoothstep(dynamicThreshold - EDGE_SOFTNESS, dynamicThreshold, finalDepth) *
                                     (1.0 - smoothstep(dynamicThreshold, dynamicThreshold + 0.1, finalDepth));
                                     
                    // Colors
                    // Colors
                    // 3.1 Boost Input Contrast & Saturation (Match Unity Post-processing)
                    vec3 sourceRGB = col.rgb;
                    
                    // Contrast (S-Curve) - Toned down
                    sourceRGB = (sourceRGB - 0.5) * 1.1 + 0.5;
                    
                    // Saturation - Toned down close to original
                    const vec3 W = vec3(0.2125, 0.7154, 0.0721);
                    vec3 intensity = vec3(dot(sourceRGB, W));
                    sourceRGB = mix(intensity, sourceRGB, 1.15);
                    
                    // Brightness Boost - Toned down
                    sourceRGB *= 1.05;
                    
                    vec3 finalRGB = mix(sourceRGB, EDGE_COLOR, edgeMask * mainMask * 2.5);
                    finalRGB = mix(finalRGB, FOG_COLOR, mainMask);
                    
                    // 4. Eye Vignette (Keeping it very subtle/wide)
                    vec2 dist = abs(finalUV - 0.5) * 2.0;
                    float vignette = 1.0 - smoothstep(1.2, 2.0, length(dist)); 
                    finalRGB *= clamp(vignette + 0.4, 0.0, 1.0); 
                    
                    // 5. Breathing Glow (HDR)
                    float emissionFactor = pow((breathCycle + 1.0) * 0.5, 2.0);
                    float totalGlow = 0.3 + (6.0 * emissionFactor); 
                    
                    float colorDist = distance(col.rgb, GLOW_TARGET_COLOR); // Use original col for mask
                    float glowMask = 1.0 - smoothstep(0.2, 0.5, colorDist);
                    
                    finalRGB += sourceRGB * totalGlow * glowMask * 0.7; // Use boosted rgb for glow
                    
                    // 6. Mouse Flashlight (Cave Illumination)
                    // Convert normalized mouse (-0.5 to 0.5) to UV space (0 to 1)
                    vec2 lightPos = uMouse + 0.5;
                    // Correct aspect ratio for circular light (assuming landscape usually)
                    float aspect = uResolution.x / uResolution.y;
                    vec2 aspectUV = finalUV;
                    aspectUV.x *= aspect;
                    vec2 aspectLightPos = lightPos;
                    aspectLightPos.x *= aspect;

                    float distToMouse = distance(aspectUV, aspectLightPos);
                    
                    // Flashlight Settings
                    float lightRadius = 0.35; // Size of the light
                    float lightFalloff = smoothstep(lightRadius, 0.0, distToMouse);
                    
                    // Light Color (Warm Torch or Magic Blue? Cave usually implies exploring with a torch)
                    // Let's use a Neutral-Warm light to reveal true colors
                    vec3 torchColor = vec3(1.0, 0.95, 0.8); 
                    
                    // Apply light: Soft Additive
                    // Reduced intensity to avoid overexposure without tone mapping
                    vec3 litColor = sourceRGB * 0.4 + torchColor * 0.1;
                    finalRGB += litColor * lightFalloff * 0.7;
                    
                    // Standard Clamp (Restore natural contrast)
                    finalRGB = clamp(finalRGB, 0.0, 1.0);

                    gl_FragColor = vec4(finalRGB, 1.0);
                }
            `;

            const uniforms = {
                uDepthMap: depthTex,
                uTime: 0.0,
                uMouse: { x: 0, y: 0 },
                uResolution: { x: container.offsetWidth, y: container.offsetHeight }
            };
            const depthFilter = new PIXI.Filter(null, fragSrc, uniforms);

            function resize() {
                // Resize DOM container to match Image Aspect Ratio
                const hero = document.getElementById('portalHero');
                if (hero && bgTex) {
                    // Ensure the container matches the image ratio EXACTLY
                    const imgRatio = bgTex.height / bgTex.width;
                    const currentWidth = hero.offsetWidth;
                    const newHeight = currentWidth * imgRatio;

                    // Apply height to container (User said: "Change the container size")
                    hero.style.height = `${newHeight}px`;
                    hero.style.padding = '0'; // Remove conflicting padding

                    // Also ensure Pixi app matches
                    if (app.renderer) app.resize();
                }

                const w = app.screen.width, h = app.screen.height;

                // Now scale is 1:1 effectively (Cover/Contain are same)
                const scale = Math.max(w / bgTex.width, h / bgTex.height);
                bgSprite.scale.set(scale);
                bgSprite.anchor.set(0.5);
                bgSprite.x = w / 2;
                bgSprite.y = h / 2;
            }

            app.stage.addChild(bgSprite);
            bgSprite.filters = [depthFilter];
            window.addEventListener('resize', resize);
            resize();

            let mouseX = 0, mouseY = 0, smoothX = 0, smoothY = 0;
            const trackingArea = document.getElementById('portalHero') || container;
            trackingArea.addEventListener('mousemove', (e) => {
                const rect = trackingArea.getBoundingClientRect();
                mouseX = (e.clientX - rect.left) / rect.width - 0.5;
                mouseY = (e.clientY - rect.top) / rect.height - 0.5;
            });
            // Removed mouseleave reset to allow light to "follow out" / drift naturally
            trackingArea.addEventListener('mouseleave', () => {
                // Optional: Push mouseX/Y slightly outside to simulate leaving? 
                // Or just do nothing and let it stay at last edge position. User asked for "follows out".
                // We'll leave it as is, which means it stays where it left.
            });
            app.ticker.add((delta) => {
                const dt = Math.min(delta, 2.0); // Cap delta to prevent jumps on lag
                smoothX += (mouseX - smoothX) * 0.25 * dt;
                smoothY += (mouseY - smoothY) * 0.25 * dt;
                depthFilter.uniforms.uTime = app.ticker.lastTime / 1000;
                depthFilter.uniforms.uMouse = { x: smoothX, y: smoothY };
                depthFilter.uniforms.uResolution = { x: app.screen.width, y: app.screen.height };
            });
        } else {
            // === PROCEDURAL FALLBACK ===
            const bgGraphics = new PIXI.Graphics();
            function drawBg() {
                bgGraphics.clear();
                bgGraphics.beginFill(0x0a0e14);
                bgGraphics.drawRect(0, 0, app.screen.width, app.screen.height);
                bgGraphics.endFill();
            }
            drawBg();
            app.stage.addChild(bgGraphics);

            const fragSrc = `
                precision mediump float;
                varying vec2 vTextureCoord;
                uniform float uTime;
                uniform vec2 uMouse;
                
                const vec3 COLOR_PRIMARY = vec3(0.0, 0.8, 0.6); // Soft Teal
                const vec3 COLOR_SECONDARY = vec3(0.0, 0.4, 0.8); // Deep Blue
                const vec3 BG_COLOR = vec3(0.05, 0.08, 0.12); // Cinematic Dark Blue-Grey
                
                void main() {
                    vec2 uv = vTextureCoord;
                    vec2 center = vec2(0.5);
                    
                    // Soft parallax
                    vec2 offset = uMouse * 0.03;
                    uv += offset * (1.0 - length(uv - center));

                    // Distance field
                    float d = distance(uv, center);
                    
                    // 1. Dynamic Atmosphere (Breathing)
                    float time = uTime * 0.2;
                    float pulse = sin(time) * 0.05 + 0.95;
                    
                    // 2. Main Glow (Softer, wider)
                    float glow = 1.0 - smoothstep(0.0, 0.8 * pulse, d);
                    glow = pow(glow, 1.5); // Soften falloff
                    
                    // 3. Wandering Highlight (The "Light Source")
                    // Instead of a hard spotlight, use a soft moving aura
                    vec2 lightPos = center + offset * 1.5;
                    float lightDist = distance(uv, lightPos);
                    float lightAura = 1.0 - smoothstep(0.0, 0.5, lightDist);
                    lightAura = pow(lightAura, 2.0);
                    
                    // 4. Color Compositing
                    vec3 color = BG_COLOR;
                    
                    // Mix primary glow
                    color = mix(color, COLOR_SECONDARY, glow * 0.4);
                    
                    // Add light source influence
                    color += COLOR_PRIMARY * lightAura * 0.3;
                    
                    // Vignette
                    float vig = 1.0 - smoothstep(0.5, 1.5, d * 1.2);
                    color *= vig;
                    
                    gl_FragColor = vec4(color, 1.0);
                }
            `;

            const uniforms = { uTime: 0.0, uMouse: { x: 0, y: 0 } };
            const shaderFilter = new PIXI.Filter(null, fragSrc, uniforms);
            bgGraphics.filters = [shaderFilter];

            let mouseX = 0, mouseY = 0, smoothX = 0, smoothY = 0;
            let isHovering = false;
            let autoTime = 0;
            const trackingArea = document.getElementById('portalHero') || container;

            trackingArea.addEventListener('mousemove', (e) => {
                isHovering = true;
                const rect = trackingArea.getBoundingClientRect();
                mouseX = (e.clientX - rect.left) / rect.width - 0.5;
                mouseY = (e.clientY - rect.top) / rect.height - 0.5;
            });

            trackingArea.addEventListener('mouseleave', () => {
                isHovering = false;
                // Don't reset immediately, let it drift
            });

            app.ticker.add((delta) => {
                const dt = Math.min(delta, 2.0);

                if (!isHovering) {
                    // Auto wander
                    autoTime += dt * 0.01;
                    mouseX = Math.sin(autoTime) * 0.3 + Math.cos(autoTime * 0.7) * 0.1;
                    mouseY = Math.cos(autoTime * 0.8) * 0.2 + Math.sin(autoTime * 1.2) * 0.1;
                }

                smoothX += (mouseX - smoothX) * 0.05 * dt;
                smoothY += (mouseY - smoothY) * 0.05 * dt;

                shaderFilter.uniforms.uTime = app.ticker.lastTime / 1000;
                shaderFilter.uniforms.uMouse = { x: smoothX, y: smoothY };
            });

            window.addEventListener('resize', drawBg);
        }
    } catch (e) {
        console.error('Shader init failed:', e);
    }
}

// ===== TALENT TREE SHADER (SKYRIM VOID) =====

function initTalentShader(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const gl = canvas.getContext('webgl');
    if (!gl) return;

    // Resize handling
    function resize() {
        canvas.width = canvas.parentElement.offsetWidth;
        canvas.height = canvas.parentElement.offsetHeight;
        gl.viewport(0, 0, canvas.width, canvas.height);
    }
    window.addEventListener('resize', resize);
    resize();

    // Vertex Shader (Simple Quad)
    const vsSource = `
        attribute vec4 aVertexPosition;
        void main() {
            gl_Position = aVertexPosition;
        }
    `;

    // Fragment Shader (Cosmic Void)
    const fsSource = `
        precision mediump float;
        uniform float uTime;
        uniform vec2 uResolution;

        // Noise functions
        float random(vec2 st) {
            return fract(sin(dot(st.xy, vec2(12.9898,78.233))) * 43758.5453123);
        }

        float noise(vec2 st) {
            vec2 i = floor(st);
            vec2 f = fract(st);
            float a = random(i);
            float b = random(i + vec2(1.0, 0.0));
            float c = random(i + vec2(0.0, 1.0));
            float d = random(i + vec2(1.0, 1.0));
            vec2 u = f * f * (3.0 - 2.0 * f);
            return mix(a, b, u.x) + (c - a)* u.y * (1.0 - u.x) + (d - b) * u.x * u.y;
        }

        float fbm(vec2 st) {
            float v = 0.0;
            float a = 0.5;
            vec2 shift = vec2(100.0);
            mat2 rot = mat2(cos(0.5), sin(0.5), -sin(0.5), cos(0.50));
            for (int i = 0; i < 5; i++) {
                v += a * noise(st);
                st = rot * st * 2.0 + shift;
                a *= 0.5;
            }
            return v;
        }

        void main() {
            vec2 uv = gl_FragCoord.xy / uResolution;
            vec2 p = (gl_FragCoord.xy - 0.5 * uResolution) / min(uResolution.y, uResolution.x);
            
            // Deep space background (subtle gradient)
            vec3 color = vec3(0.0); 

            // Nebula fog - Slower, more ethereal
            float t = uTime * 0.15;
            float n1 = fbm(p * 1.5 + vec2(t*0.3, t*0.15));
            float n2 = fbm(p * 3.0 - vec2(t*0.1, t*0.25));
            
            // Nebula Color Mixing - Deep blue/purple Skyrim style
            vec3 nebulaColor1 = vec3(0.1, 0.15, 0.4); // Deep blue
            vec3 nebulaColor2 = vec3(0.25, 0.1, 0.35); // Deep purple
            vec3 nebulaColor = mix(nebulaColor1, nebulaColor2, n1);
            
            // Very subtle intensity
            float intensity = n2 * 0.35;
            color += nebulaColor * intensity;

            // Stars - Multiple layers for depth
            float starNoise = random(gl_FragCoord.xy);
            
            // Distant tiny stars (many)
            if (starNoise > 0.992) {
                float s_intensity = random(gl_FragCoord.xy + 1.0) * 0.5 + 0.5;
                float twinkle = sin(uTime * 3.0 + s_intensity * 8.0) * 0.3 + 0.7;
                color += vec3(0.8, 0.85, 1.0) * s_intensity * twinkle * 0.6;
            }
            
            // Medium stars (some)
            if (starNoise > 0.998) {
                float s_intensity = random(gl_FragCoord.xy + 2.0);
                float twinkle = sin(uTime * 4.0 + s_intensity * 12.0) * 0.4 + 0.6;
                color += vec3(1.0, 0.95, 0.9) * s_intensity * twinkle * 1.2;
            }
            
            // Bright stars (rare)
            if (starNoise > 0.9995) {
                float s_intensity = random(gl_FragCoord.xy + 3.0) * 0.3 + 0.7;
                float twinkle = sin(uTime * 2.0 + s_intensity * 6.0) * 0.5 + 0.5;
                // Add colored stars
                vec3 starColor = mix(vec3(1.0, 0.9, 0.8), vec3(0.8, 0.9, 1.0), random(gl_FragCoord.xy + 4.0));
                color += starColor * s_intensity * twinkle * 2.0;
            }

            // Subtle vignette
            float vignette = smoothstep(1.8, 0.4, length(p));
            color *= vignette;
            
            gl_FragColor = vec4(color, 1.0);
        }
    `;

    // Compile Shaders
    function compileShader(gl, source, type) {
        const shader = gl.createShader(type);
        gl.shaderSource(shader, source);
        gl.compileShader(shader);
        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
            console.error(gl.getShaderInfoLog(shader));
            gl.deleteShader(shader);
            return null;
        }
        return shader;
    }

    const shaderProgram = gl.createProgram();
    gl.attachShader(shaderProgram, compileShader(gl, vsSource, gl.VERTEX_SHADER));
    gl.attachShader(shaderProgram, compileShader(gl, fsSource, gl.FRAGMENT_SHADER));
    gl.linkProgram(shaderProgram);

    if (!gl.getProgramParameter(shaderProgram, gl.LINK_STATUS)) {
        return;
    }

    // Buffers
    const positionBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    const positions = [
        -1.0, 1.0,
        1.0, 1.0,
        -1.0, -1.0,
        1.0, -1.0,
    ];
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(positions), gl.STATIC_DRAW);

    // Locations
    const aVertexPosition = gl.getAttribLocation(shaderProgram, 'aVertexPosition');
    const uTime = gl.getUniformLocation(shaderProgram, 'uTime');
    const uResolution = gl.getUniformLocation(shaderProgram, 'uResolution');

    // Loop
    function render(now) {
        if (!document.getElementById(canvasId)) return; // Stop if removed

        now *= 0.001;
        gl.viewport(0, 0, canvas.width, canvas.height);
        gl.useProgram(shaderProgram);

        gl.enableVertexAttribArray(aVertexPosition);
        gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
        gl.vertexAttribPointer(aVertexPosition, 2, gl.FLOAT, false, 0, 0);

        gl.uniform1f(uTime, now);
        gl.uniform2f(uResolution, canvas.width, canvas.height);

        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

        requestAnimationFrame(render);
    }
    requestAnimationFrame(render);
}

// Export for usage
window.initTalentShader = initTalentShader;
