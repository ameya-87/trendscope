document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('three-canvas');
    if (!canvas) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });

    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // Custom Neon Lighting
    const ambientLight = new THREE.AmbientLight(0x111827, 0.6);
    scene.add(ambientLight);

    // Glowing purple light
    const purpleLight = new THREE.DirectionalLight(0x8b5cf6, 1.5);
    purpleLight.position.set(5, 8, 5);
    scene.add(purpleLight);

    // Glowing cyan light
    const cyanLight = new THREE.DirectionalLight(0x06b6d4, 1.5);
    cyanLight.position.set(-5, -8, 4);
    scene.add(cyanLight);

    // Soft pink secondary fill light
    const pinkLight = new THREE.PointLight(0xec4899, 1, 30);
    pinkLight.position.set(0, 0, 8);
    scene.add(pinkLight);

    camera.position.z = 12;

    const trendsGroup = new THREE.Group();
    scene.add(trendsGroup);

    const tvGroup = new THREE.Group();
    scene.add(tvGroup);

    async function fetchAndVisualizeTrends() {
        try {
            const response = await fetch('/api/trends_momentum');
            const data = await response.json();

            if (!Array.isArray(data) || data.length === 0) {
                return;
            }

            // Clear previous trends
            while(trendsGroup.children.length > 0){
                trendsGroup.remove(trendsGroup.children[0]);
            }

            // Normalize momentum for better visualization
            const momentums = data.map(t => t.momentum || 0);
            const maxMomentum = Math.max(...momentums.map(Math.abs));
            const momentumScale = maxMomentum > 0 ? 4 / maxMomentum : 0;

            data.forEach((trend, index) => {
                const geometry = new THREE.SphereGeometry(0.4, 24, 24);
                
                let colorHex = 0x8b5cf6; // Cyber Purple as default
                if (trend.trend_direction === 'up') {
                    colorHex = 0x10b981; // Neon Green for up
                } else if (trend.trend_direction === 'down') {
                    colorHex = 0xef4444; // Neon Red for down
                }
                
                const color = new THREE.Color(colorHex);
                const material = new THREE.MeshStandardMaterial({ 
                    color: color,
                    emissive: color,
                    emissiveIntensity: 0.15,
                    roughness: 0.2,
                    metalness: 0.8
                });
                
                const sphere = new THREE.Mesh(geometry, material);

                // Position spheres in a floating orbit
                const angle = (index / data.length) * Math.PI * 2;
                const radius = 6;
                sphere.position.x = Math.cos(angle) * radius;
                sphere.position.y = Math.sin(angle) * radius;
                sphere.position.z = (trend.momentum || 0) * momentumScale;

                // Scale based on latest_value
                const scale = Math.min(2.0, 0.4 + (trend.latest_value / 80));
                sphere.scale.set(scale, scale, scale);

                trendsGroup.add(sphere);
            });

        } catch (error) {
            console.error('Error fetching/visualizing trends momentum:', error);
        }
    }

    async function fetchAndVisualizeTvTrends() {
        try {
            const response = await fetch('/api/tv_trends');
            const data = await response.json();

            if (!Array.isArray(data) || data.length === 0) {
                return;
            }

            // Clear previous TV trends
            while(tvGroup.children.length > 0){
                tvGroup.remove(tvGroup.children[0]);
            }

            // Create metallic glass toruses for TV topics
            data.forEach((trend, index) => {
                const count = trend.count != null ? trend.count : (trend.rating != null ? trend.rating * 10 : 0);
                const radius = 1.2 + Math.min(2.5, count * 0.08);
                const tube = 0.08 + Math.min(0.2, count * 0.015);
                const geometry = new THREE.TorusGeometry(radius, tube, 12, 48);

                const hue = (index * 45) % 360;
                const color = new THREE.Color(`hsl(${hue}, 90%, 55%)`);
                const material = new THREE.MeshStandardMaterial({ 
                    color: color, 
                    emissive: color,
                    emissiveIntensity: 0.1,
                    metalness: 0.9,
                    roughness: 0.1,
                    transparent: true,
                    opacity: 0.35
                });
                const torus = new THREE.Mesh(geometry, material);

                const angle = (index / data.length) * Math.PI * 2;
                const baseRadius = 9;
                torus.position.x = Math.cos(angle) * baseRadius;
                torus.position.y = Math.sin(angle) * baseRadius;
                torus.position.z = -5;

                torus.rotation.x = Math.random() * Math.PI;
                torus.rotation.y = Math.random() * Math.PI;

                tvGroup.add(torus);
            });

        } catch (error) {
            console.error('Error fetching/visualizing TV trends:', error);
        }
    }

    fetchAndVisualizeTrends();
    fetchAndVisualizeTvTrends();
    
    // Refresh data every 60 seconds
    setInterval(fetchAndVisualizeTrends, 60000);
    setInterval(fetchAndVisualizeTvTrends, 60000);

    function animate() {
        requestAnimationFrame(animate);

        trendsGroup.rotation.y += 0.003;
        trendsGroup.rotation.x += 0.001;
        
        tvGroup.rotation.y -= 0.002;
        tvGroup.rotation.x -= 0.001;

        renderer.render(scene, camera);
    }

    animate();

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
});