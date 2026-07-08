document.addEventListener('DOMContentLoaded', () => {
    const canvas = document.getElementById('three-canvas');
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true });

    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);

    // Add some lighting
    const ambientLight = new THREE.AmbientLight(0xcccccc, 0.5);
    scene.add(ambientLight);
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(1, 1, 1).normalize();
    scene.add(directionalLight);

    camera.position.z = 10;

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
            const momentumScale = maxMomentum > 0 ? 5 / maxMomentum : 0;

            data.forEach((trend, index) => {
                const geometry = new THREE.SphereGeometry(0.5, 32, 32);
                let color = 0x00ff00; // Default green
                if (trend.trend_direction === 'up') {
                    color = 0x0000ff; // Blue for up
                } else if (trend.trend_direction === 'down') {
                    color = 0xff0000; // Red for down
                }
                const material = new THREE.MeshPhongMaterial({ color: color });
                const sphere = new THREE.Mesh(geometry, material);

                // Position spheres in a circle or grid
                const angle = (index / data.length) * Math.PI * 2;
                const radius = 5;
                sphere.position.x = Math.cos(angle) * radius;
                sphere.position.y = Math.sin(angle) * radius;
                sphere.position.z = (trend.momentum || 0) * momentumScale; // Use normalized momentum for Z position

                // Scale based on latest_value, clamped to avoid excessively large spheres
                const scale = Math.min(2, 0.5 + (trend.latest_value / 100)); // Assuming latest_value is 0-100
                sphere.scale.set(scale, scale, scale);

                trendsGroup.add(sphere);
            });

        } catch (error) {
            console.error('Error fetching or visualizing trends momentum:', error);
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

            // Create colorful torus for TV topics
            data.forEach((trend, index) => {
                const count = trend.count != null ? trend.count : (trend.rating != null ? trend.rating * 10 : 0);
                const radius = 6 + Math.min(4, count * 0.2);
                const tube = 0.2 + Math.min(0.6, count * 0.05);
                const geometry = new THREE.TorusGeometry(radius > 0 ? 1 : 1, tube > 0 ? 0.2 : 0.2, 16, 100);

                const hue = (index * 27) % 360;
                const color = new THREE.Color(`hsl(${hue}, 85%, 60%)`);
                const material = new THREE.MeshPhongMaterial({ color, emissive: color.clone().multiplyScalar(0.2) });
                const torus = new THREE.Mesh(geometry, material);

                const angle = (index / data.length) * Math.PI * 2;
                const baseRadius = 8;
                torus.position.x = Math.cos(angle) * baseRadius;
                torus.position.y = Math.sin(angle) * baseRadius;
                torus.position.z = -4;

                torus.rotation.x = Math.random() * Math.PI;
                torus.rotation.y = Math.random() * Math.PI;

                tvGroup.add(torus);
            });

        } catch (error) {
            console.error('Error fetching or visualizing TV trends:', error);
        }
    }

    fetchAndVisualizeTrends();
    fetchAndVisualizeTvTrends();
    // Refresh data every 30 seconds
    setInterval(fetchAndVisualizeTrends, 30000);
    setInterval(fetchAndVisualizeTvTrends, 30000);

    function animate() {
        requestAnimationFrame(animate);

        trendsGroup.rotation.y += 0.005;
        tvGroup.rotation.x += 0.003;

        renderer.render(scene, camera);
    }

    animate();

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
});