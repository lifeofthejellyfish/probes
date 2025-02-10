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
PROBE_REPLICATION_COST = {"minerals": 70, "gases": 70, "energy":0}  # Cost in each resource
MAX_PROBES = 100
COMMUNICATION_RADIUS = 200  # Introduce a communication radius


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

    def mine_resource(self, resource_type, amount):
        if resource_type == "minerals":
            mined = min(amount, self.minerals)
            self.minerals -= mined
            return mined
        elif resource_type == "gases":
            mined = min(amount, self.gases)
            self.gases -= mined
            return mined
        elif resource_type == "energy":
            mined = min(amount, self.energy)
            self.energy -= mined
            return mined
        return 0

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
    def __init__(self, x, y, stars, speed=2):
        self.x = x
        self.y = y
        self.speed = speed
        self.cargo = {"minerals": 0, "gases": 0, "energy": 0}
        self.target = None
        self.state = "idle"
        self.probes = []
        self.stars = stars  # Store the stars in the probe instance
        self.is_mining = False  # Flag to track if the probe is currently mining
        self.max_cargo = {"minerals": 200, "gases": 200, "energy": 200}  # Set max capacity for each resource
        self.visited_stars = set()  # Keep track of visited stars

    def set_target(self, target, state):
        self.target = target
        self.state = state
        if isinstance(target, Star):
            print(f"Probe at ({self.x:.1f}, {self.y:.1f}) assigned to star at ({target.x:.1f}, {target.y:.1f})")
        elif isinstance(target, Colony):
            print(f"Probe at ({self.x:.1f}, {self.y:.1f}) returning to colony.")

    def find_nearest_star(self):
        nearest_star = None
        nearest_distance = float('inf')
        needed_resources = self.needs_resources()

        if needed_resources:
            for star in self.stars:
                if star in self.visited_stars:  # Skip visited stars
                    continue
                for resource in needed_resources:
                    if getattr(star, resource) > 0:
                        distance = math.hypot(star.x - self.x, star.y - self.y)
                        if distance < nearest_distance:
                            nearest_distance = distance
                            nearest_star = star
                        break  # Check next star
            if nearest_star:
                self.visited_stars.add(nearest_star)  # Mark as visited
        return nearest_star

    def needs_resources(self):
        # Determine which resources are needed
        needed = {}
        for resource, amount in self.cargo.items():
            if amount < self.max_cargo[resource]:
                needed[resource] = self.max_cargo[resource] - amount
        return needed

    def find_star_with_resource(self, resource):
        # Find a star that has the specified resource
        for star in self.stars:
            if star in self.visited_stars:  # Skip stars that have been visited
                continue
            if getattr(star, resource) > 0:  # Check if the star has the resource
                self.visited_stars.add(star)  # Once a star has been looked at mark it
                return star
        return None

    def update(self, other_probes):
        self.communicate(other_probes)  # Pass the list of other probes

        if self.target:
            dx = self.target.x - self.x
            dy = self.target.y - self.y
            distance = math.hypot(dx, dy)

            # *** MOVE THE PROBE FIRST ***
            if distance > self.speed:  # Only move if not already at target
                # Normalize the vector
                dx, dy = dx / distance, dy / distance
                self.x += dx * self.speed
                self.y += dy * self.speed
                # Recalculate distance after movement
                distance = math.hypot(self.target.x - self.x, self.target.y - self.y)

            # *** THEN CHECK FOR ARRIVAL ***
            if distance <= self.speed:  # Arrived at target
                if isinstance(self.target, Star):
                    if self.target.total_resources() > 0:
                        needed_resources = self.needs_resources()
                        if needed_resources:
                            resource_to_mine = next(iter(needed_resources))
                            available_resources = getattr(self.target, resource_to_mine)

                            # *** IMPROVED MINING AMOUNT CALCULATION ***
                            mining_amount = min(self.speed, self.max_cargo[resource_to_mine] - self.cargo[resource_to_mine], available_resources)
                            if mining_amount > 0:  # only mine if we can mine something
                                mined_amount = self.target.mine_resource(resource_to_mine, mining_amount)
                                self.cargo[resource_to_mine] += mined_amount
                                print(f"Probe mined {mined_amount} {resource_to_mine} from star. Cargo: {self.cargo}")  # Added Mined Amount

                                if self.target.total_resources() <= 0:
                                    print(f"Star at ({self.target.x:.1f}, {self.target.y:.1f}) is depleted.")  # Added float formatting
                                    self.target = None
                                    self.state = "idle"  # Reset state *before* retargeting
                                    self.set_target(self.find_nearest_star(), "traveling_to_star")
                                    return
                            else:  # Added else statement for clarity
                                star_coords_str = f"({self.target.x:.1f}, {self.target.y:.1f})"
                                print(f"Star at {star_coords_str} does not have enough {resource_to_mine} or cargo full. Only {available_resources} available. Cargo: {self.cargo}")
                                self.target = None
                                self.state = "idle"  # Reset state *before* retargeting
                                self.set_target(self.find_nearest_star(), "traveling_to_star")
                                return

                        else:
                            print(f"Probe has all resources. Finding a new target.")
                            self.target = None
                            self.state = "idle"  # Reset state *before* retargeting
                            self.set_target(self.find_nearest_star(), "traveling_to_star")
                            return

                    else:
                        print(f"Star at ({self.target.x:.1f}, {self.target.y:.1f}) is depleted.")  # Added float formatting
                        self.target = None
                        self.state = "idle"  # Reset state *before* retargeting
                        self.set_target(self.find_nearest_star(), "traveling_to_star")
                        return

                elif isinstance(self.target, Colony):
                    # Deposit cargo into the colony.
                    self.target.deposit(
                        int(self.cargo["minerals"]),
                        int(self.cargo["gases"]),
                        int(self.cargo["energy"])
                    )
                    print(f"Probe delivered resources to colony: {self.cargo}")  # Keep this for important info
                    self.cargo = {"minerals": 0, "gases": 0, "energy": 0}
                    self.target = None
                    self.state = "idle"
                    self.is_mining = False  # Reset mining flag
                    self.visited_stars = set()  # Clear visited stars on returning to colony

                elif isinstance(self.target, ExplorationTarget):
                    # When a probe on an exploration mission arrives, it discovers an anomaly.
                    bonus = random.randint(20, 50)
                    self.target.colony.deposit(bonus, bonus, bonus)
                    print(f"Probe discovered an anomaly! Bonus resources: ")
                    self.target = None
                    self.state = "idle"
                    self.is_mining = False  # Reset mining flag

        else:  # No Target. Find Target.
            needed_resources = self.needs_resources()
            if needed_resources:
                for resource in needed_resources:
                    star = self.find_star_with_resource(resource)
                    if star:
                        self.set_target(star, "traveling_to_star")
                        return  # Prevent trying to find another target this cycle
            # If we didn't find a specific resource, fall back to any nearest star. BUT still check visited.
            self.set_target(self.find_nearest_star(), "traveling_to_star")
            return  # Prevent trying to find another target this cycle

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
            new_probe = Probe(self.x, self.y, self.stars)  # Spawn at current location
            self.probes.append(new_probe)
            print(f"New probe created! Total probes: {len(self.probes)}")
            # Assign a target to the new probe
            new_probe.set_target(new_probe.find_nearest_star(), "traveling_to_star")  # Give it a target

    def communicate(self, other_probes):
        # Communicate Depleted Stars
        for other_probe in other_probes:
            if other_probe != self:  # Don't communicate with itself
                distance = math.hypot(self.x - other_probe.x, self.y - other_probe.y)
                if distance <= COMMUNICATION_RADIUS:
                    other_probe.visited_stars.update(self.visited_stars)

    def is_hovered(self, mouse_x, mouse_y, zoom_level, offset_x, offset_y):
        radius = 5 * zoom_level
        draw_x = int((self.x - offset_x) * zoom_level)
        draw_y = int((self.y - offset_y) * zoom_level)
        return (draw_x - radius <= mouse_x <= draw_x + radius) and (draw_y - radius <= mouse_y <= draw_y + radius)


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
    # Initialize probes *after* stars to pass star list.
    probes = [Probe(WORLD_WIDTH // 2, WORLD_HEIGHT // 2, stars)]
    colony = Colony(WORLD_WIDTH // 2, WORLD_HEIGHT // 2)
    # Make additional initial probes
    probes[0].replicate()
    probes[0].replicate()
    probes[0].replicate()

    zoom_level = 1.0
    offset_x = colony.x - WIDTH / (2 * zoom_level)
    offset_y = colony.y - HEIGHT / (2 * zoom_level)

    font = pygame.font.Font(None, 30)

    running = True
    mouse_x, mouse_y = 0, 0  # Initialize mouse position variables

    while running:
        clock.tick(200)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEWHEEL:
                # Zoom update event
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
                mouse_x, mouse_y = event.pos  # Get the current mouse position
                if event.buttons[0]:
                    offset_x -= event.rel[0] / zoom_level
                    offset_y -= event.rel[1] / zoom_level
                    offset_x = max(0, min(offset_x, WORLD_WIDTH - WIDTH / zoom_level))
                    offset_y = max(0, min(offset_y, WORLD_HEIGHT - HEIGHT / zoom_level))

        for probe in probes:
            probe.update(probes)  # Pass the list of probes to each probe's update method
        # Replicate the probe after other probes have been updated, and replicate only once per tick
        for probe in probes:  
            probe.replicate()
        # Communicate after all probes have updated and replicated
        for i in range(len(probes)):
            probes[i].communicate(probes)

        screen.fill((0, 0, 20))

        for star in stars:
            star.draw(screen, offset_x, offset_y, zoom_level)
        for probe in probes:
            probe.draw(screen, offset_x, offset_y, zoom_level)

            # Check if the mouse is hovering over the probe
            if probe.is_hovered(mouse_x, mouse_y, zoom_level, offset_x, offset_y):
                # Draw the tooltip
                tooltip_text = f"Status: {probe.state}, Cargo: {probe.cargo}"
                tooltip_surface = font.render(tooltip_text, True, (255, 255, 255))
                screen.blit(tooltip_surface, (mouse_x + 10, mouse_y + 10))  # Offset the tooltip slightly

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