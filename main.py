import pygame
import random
import math
import noise

# --------------------------
# Constants & Configurations
# --------------------------
WIDTH, HEIGHT = 1200, 900
WORLD_WIDTH = 4000
WORLD_HEIGHT = 4000
MIN_STAR_DISTANCE = 15
STAR_RESOURCE_RANGE = (50, 200)  # Keep this, but it applies to each resource type
PROBE_REPLICATION_COST = {"minerals": 70, "gases": 70, "energy":60}  # Cost in each resource
MAX_PROBES = 100


# --------------------------
# Star Class
# --------------------------
class Star:
    def __init__(self, x, y, size_mod=1.0):
        self.x = x
        self.y = y
        self.size_mod = size_mod
        # Generate random color and use RGB for resources
        self.color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        self.minerals = int(self.color[0] / 255 * (STAR_RESOURCE_RANGE[1] - STAR_RESOURCE_RANGE[0]) + STAR_RESOURCE_RANGE[0])
        self.gases = int(self.color[1] / 255 * (STAR_RESOURCE_RANGE[1] - STAR_RESOURCE_RANGE[0]) + STAR_RESOURCE_RANGE[0])
        self.energy = int(self.color[2] / 255 * (STAR_RESOURCE_RANGE[1] - STAR_RESOURCE_RANGE[0]) + STAR_RESOURCE_RANGE[0])
        self.visits = 0  # Initialize visits to track how many times this star has been mined

    def draw(self, screen, offset_x, offset_y, zoom_level):
        radius = 3 * zoom_level * self.size_mod
        draw_x = int((self.x - offset_x) * zoom_level)
        draw_y = int((self.y - offset_y) * zoom_level)
        if 0 - radius <= draw_x <= WIDTH + radius and 0 - radius <= draw_y <= HEIGHT + radius:
            pygame.draw.circle(screen, self.color, (draw_x, draw_y), radius)  # Use the star's color

    def total_resources(self):
        return self.minerals + self.gases + self.energy

# --------------------------
# Colony Class
# --------------------------
class Colony:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.minerals = 0
        self.gases = 0
        self.energy = 0

    def deposit(self, minerals, gases, energy):
        self.minerals += minerals
        self.gases += gases
        self.energy += energy

    def draw(self, screen, offset_x, offset_y, zoom_level):
        radius = 10 * zoom_level
        draw_x = int((self.x - offset_x) * zoom_level)
        draw_y = int((self.y - offset_y) * zoom_level)
        if 0 - radius <= draw_x <= WIDTH + radius and 0 - radius <= draw_y <= HEIGHT + radius:
            pygame.draw.circle(screen, (0, 0, 255), (draw_x, draw_y), radius)

# --------------------------
# Probe Class
# --------------------------
class Probe:
    def __init__(self, x, y, speed=2, capacity=50):
        self.x = x
        self.y = y
        self.speed = speed
        self.capacity = capacity
        self.cargo = {"minerals": 0, "gases": 0, "energy": 0}
        self.target = None
        self.state = "idle"
        self.probes = []

    def set_target(self, target, state):
        self.target = target
        self.state = state
        if isinstance(target, Star):
            print(f"Probe at ({self.x:.1f}, {self.y:.1f}) assigned to star at ({target.x}, {target.y})")
        elif isinstance(target, Colony):
            print(f"Probe at ({self.x:.1f}, {self.y:.1f}) returning to colony.")

    def find_nearest_star(self):
        nearest_star = None
        nearest_distance = float('inf')
        
        for star in stars:  # Assuming 'stars' is accessible here
            if star.total_resources() > 0:  # Only consider stars with resources
                distance = math.hypot(star.x - self.x, star.y - self.y)
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_star = star
                    
        return nearest_star

    def update(self):
        self.communicate()
        self.replicate()
        
        if self.target:
            dx = self.target.x - self.x
            dy = self.target.y - self.y
            distance = math.hypot(dx, dy)
            if distance < self.speed:
                if isinstance(self.target, Star):
                    # Check if the star has resources before mining
                    if self.target.total_resources() > 0:
                        # Existing mining logic...
                        total_cargo = self.cargo["minerals"] + self.cargo["gases"] + self.cargo["energy"]
                        mining_amount = min(10, self.capacity - total_cargo)
                        total_color_value = sum(self.target.color)
                        fraction_minerals = self.target.color[0] / total_color_value
                        fraction_gases = self.target.color[1] / total_color_value
                        fraction_energy = self.target.color[2] / total_color_value
                        desired_minerals = int(mining_amount * fraction_minerals)
                        desired_gases = int(mining_amount * fraction_gases)
                        desired_energy = int(mining_amount * fraction_energy)
                        minerals_mined = min(desired_minerals, self.target.minerals)
                        gases_mined = min(desired_gases, self.target.gases)
                        energy_mined = min(desired_energy, self.target.energy)
                        self.cargo["minerals"] += minerals_mined
                        self.cargo["gases"] += gases_mined
                        self.cargo["energy"] += energy_mined
                        self.target.minerals -= minerals_mined
                        self.target.gases -= gases_mined
                        self.target.energy -= energy_mined
                        self.target.visits += 1
                        print(f"Probe mined from star. Cargo: {self.cargo}")
                        self.target = None
                        self.state = "idle"
                    else:
                        print(f"Star at ({self.target.x}, {self.target.y}) is depleted. Returning to colony.")
                        self.target = None  # Clear target if star is depleted
                        self.set_target(self.state.colony, "returning")  # Return to colony
                elif isinstance(self.target, Colony):
                    # Deposit cargo into the colony.
                    self.target.deposit(
                        int(self.cargo["minerals"]),
                        int(self.cargo["gases"]),
                        int(self.cargo["energy"])
                    )
                    print(f"Probe delivered resources to colony: {self.cargo}")
                    self.cargo = {"minerals": 0, "gases": 0, "energy": 0}
                    self.target = None
                    self.state = "idle"

                elif isinstance(self.target, ExplorationTarget):
                    # When a probe on an exploration mission arrives, it discovers an anomaly.
                    bonus = random.randint(20, 50)
                    self.target.colony.deposit(bonus, bonus, bonus)
                    print(f"Probe discovered an anomaly! Bonus resources: {bonus}")
                    self.target = None
                    self.state = "idle"
            else:
                # Move towards the target
                dx, dy = dx / distance, dy / distance
                self.x += dx * self.speed
                self.y += dy * self.speed
        else:
            # Find a new target if none is set
            self.set_target(self.find_nearest_star(), "traveling_to_star")

    def draw(self, screen, offset_x, offset_y, zoom_level):
        radius = 5 * zoom_level
        draw_x = int((self.x - offset_x) * zoom_level)
        draw_y = int((self.y - offset_y) * zoom_level)
        if 0 - radius <= draw_x <= WIDTH + radius and 0 - radius <= draw_y <= HEIGHT + radius:
            pygame.draw.circle(screen, (0, 255, 0), (draw_x, draw_y), radius)
        if self.target:
            target_draw_x = int((self.target.x - offset_x) * zoom_level)
            target_draw_y = int((self.target.y - offset_y) * zoom_level)
            pygame.draw.line(
                screen,
                (255, 0, 0),
                (draw_x, draw_y),
                (target_draw_x, target_draw_y),
                int(1 * max(zoom_level, 0.1)),
            )

    def deposit(self, minerals, gases, energy):
        if isinstance(self.target, Colony):
            self.target.deposit(minerals, gases, energy)

    def replicate(self):
        if (len(self.probes) < MAX_PROBES and
                self.cargo["minerals"] >= PROBE_REPLICATION_COST["minerals"] and
                self.cargo["gases"] >= PROBE_REPLICATION_COST["gases"] and
                self.cargo["energy"] >= PROBE_REPLICATION_COST["energy"]):
            self.cargo["minerals"] -= PROBE_REPLICATION_COST["minerals"]
            self.cargo["gases"] -= PROBE_REPLICATION_COST["gases"]
            self.cargo["energy"] -= PROBE_REPLICATION_COST["energy"]
            new_probe = Probe(self.x, self.y)  # Spawn at current location
            self.probes.append(new_probe)
            print(f"New probe created! Total probes: {len(self.probes)}")

    def communicate(self):
        # Logic for probes to share information about resources or targets
        for probe in self.probes:
            if probe != self:  # Don't communicate with itself
                # Example: share cargo status
                print(f"Probe at ({self.x:.1f}, {self.y:.1f}) shares cargo: {self.cargo}")


class ExplorationTarget:
    def __init__(self, x, y, colony):
        self.x = x
        self.y = y
        self.colony = colony

# --------------------------
# Galaxy Generation Function
# --------------------------
def generate_galaxy(world_width, world_height, num_stars):
    stars = []
    scale = 100.0
    octaves = 4
    persistence = 0.5
    lacunarity = 2.0
    density_threshold = 0.1

    for _ in range(num_stars):
        while True:
            x = random.uniform(0, world_width)
            y = random.uniform(0, world_height)
            nx = x / scale
            ny = y / scale
            noise_val = noise.pnoise2(nx, ny, octaves=octaves, persistence=persistence, lacunarity=lacunarity,
                                      repeatx=world_width / scale, repeaty=world_height / scale, base=0)
            noise_val = (noise_val + 1) / 2
            if noise_val > density_threshold:
                size_mod = 1.0 + (noise_val - density_threshold) * 0.5  # Denser regions get bigger stars
                valid_location = True
                for star in stars:
                    if math.hypot(x - star.x, y - star.y) < MIN_STAR_DISTANCE:
                        valid_location = False
                        break
                if valid_location:
                    stars.append(Star(x, y, size_mod))  # Pass only x, y, and size_mod
                    break
    return stars

# --------------------------
# Main Simulation Function
# --------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Matrioshka Brain Galactic Colony Simulation")
    clock = pygame.time.Clock()

    stars = generate_galaxy(WORLD_WIDTH, WORLD_HEIGHT, 2000)
    probes = [Probe(WORLD_WIDTH // 2, WORLD_HEIGHT // 2)]
    colony = Colony(WORLD_WIDTH // 2, WORLD_HEIGHT // 2)

    zoom_level = 1.0
    offset_x = colony.x - WIDTH / (2 * zoom_level)
    offset_y = colony.y - HEIGHT / (2 * zoom_level)

    font = pygame.font.Font(None, 30)

    running = True
    while running:
        clock.tick(200)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEWHEEL:
                zoom_level += event.y * 0.1
                zoom_level = max(0.1, min(zoom_level, 5.0))
                mouse_x, mouse_y = pygame.mouse.get_pos()
                world_x_before = offset_x + mouse_x / zoom_level
                world_y_before = offset_y + mouse_y / zoom_level
                zoom_level += event.y * 0.1
                zoom_level = max(0.1, min(zoom_level, 5.0))
                offset_x = world_x_before - mouse_x / zoom_level
                offset_y = world_y_before - mouse_y / zoom_level
                offset_x = max(0, min(offset_x, WORLD_WIDTH - WIDTH / zoom_level))
                offset_y = max(0, min(offset_y, WORLD_HEIGHT - HEIGHT / zoom_level))
            elif event.type == pygame.MOUSEMOTION:
                if event.buttons[0]:
                    offset_x -= event.rel[0] / zoom_level
                    offset_y -= event.rel[1] / zoom_level
                    offset_x = max(0, min(offset_x, WORLD_WIDTH - WIDTH / zoom_level))
                    offset_y = max(0, min(offset_y, WORLD_HEIGHT - HEIGHT / zoom_level))

        for probe in probes:
            probe.update()
            probe.replicate()

        screen.fill((0, 0, 20))

        for star in stars:
            star.draw(screen, offset_x, offset_y, zoom_level)
        for probe in probes:
            probe.draw(screen, offset_x, offset_y, zoom_level)
        colony.draw(screen, offset_x, offset_y, zoom_level)

        # Display all three resource types
        resource_text = font.render(
            f"Colony: Min={colony.minerals}, Gas={colony.gases}, Energy={colony.energy}",
            True,
            (255, 255, 255),
        )
        screen.blit(resource_text, (10, 10))

        probe_count_text = font.render(
            f"Probes: {len(probes)}", True, (255, 255, 255)
        )
        screen.blit(probe_count_text, (10, 40))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()