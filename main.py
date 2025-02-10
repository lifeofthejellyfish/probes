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
PROBE_REPLICATION_COST = {"minerals": 70, "gases": 70, "energy": 0}  # Cost in each resource
MAX_PROBES = 100
COMMUNICATION_RADIUS = 200  # Introduce a communication radius
REPLICATION_COOLDOWN_TIME = 100  # Cooldown in frames
PROBE_CONSTRUCTION_THRESHOLD = 200  # Colony resource threshold to trigger probe construction
PROBE_SPEED_UPGRADE_RESEARCH_COST = 150
PROBE_SPEED_UPGRADE_AMOUNT = 1
RESEARCH_LAB_BUILD_COST = {"minerals": 800, "gases": 400}  # Increased build cost significantly!
RESEARCH_LAB_RESEARCH_RATE = 1
RESEARCH_LAB_BUILD_THRESHOLD = 600  # Colony resource threshold to trigger lab construction


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
        self.research = random.randint(20, 100)
        self.visits = 0  # Initialize visits to track how many times this star has been mined

    def draw(self, screen, offset_x, offset_y, zoom_level):
        radius = 3 * zoom_level * self.size_mod
        draw_x = int((self.x - offset_x) * zoom_level)
        draw_y = int((self.y - offset_y) * zoom_level)
        if 0 - radius <= draw_x <= WIDTH + radius and 0 - radius <= draw_y <= HEIGHT + radius:
            pygame.draw.circle(screen, self.color, (draw_x, draw_y), radius)  # Use the star's color

    def total_resources(self):
        return self.minerals + self.gases + self.energy + self.research

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
        elif resource_type == "research":
            mined = min(amount, self.research)
            self.research -= mined
            return mined
        return 0

# --------------------------
# Colony Class
# --------------------------
class Colony:
    def __init__(self, x, y, stars):  # Added stars parameter
        self.x = x
        self.y = y
        self.minerals = 0
        self.gases = 0
        self.energy = 0
        self.research = 0
        self.stars = stars  # Store stars for probe construction
        self.probe_construction_timer = 0  # Timer to control probe construction frequency
        self.probe_speed_researched = False  # Track if speed upgrade is researched
        self.research_labs = 0
        self.lab_construction_timer = 0  # Timer to control lab construction frequency

    def deposit(self, minerals, gases, energy, research=0):
        self.minerals += minerals
        self.gases += gases
        self.energy += energy
        self.research += research

    def draw(self, screen, offset_x, offset_y, zoom_level):
        radius = 10 * zoom_level
        draw_x = int((self.x - offset_x) * zoom_level)
        draw_y = int((self.y - offset_y) * zoom_level)
        if 0 - radius <= draw_x <= WIDTH + radius and 0 - radius <= draw_y <= HEIGHT + radius:
            pygame.draw.circle(screen, (0, 0, 255), (draw_x, draw_y), radius)

    def construct_probe(self):
        if (self.minerals >= PROBE_REPLICATION_COST["minerals"] and
                self.gases >= PROBE_REPLICATION_COST["gases"]):  # Energy is free for probes

            self.minerals -= PROBE_REPLICATION_COST["minerals"]
            self.gases -= PROBE_REPLICATION_COST["gases"]

            probe_speed = 2  # Base speed
            if self.probe_speed_researched:  # Apply speed upgrade if researched
                probe_speed += PROBE_SPEED_UPGRADE_AMOUNT

            new_probe = Probe(self.x, self.y, self.stars, self, speed=probe_speed)  # Colony is now self, pass speed
            new_probe.set_target(new_probe.find_nearest_star(), "traveling_to_star")
            return new_probe
        return None

    def research_probe_speed_upgrade(self):
        if not self.probe_speed_researched:  # Only research if not already done
            if self.research >= PROBE_SPEED_UPGRADE_RESEARCH_COST:
                self.research -= PROBE_SPEED_UPGRADE_RESEARCH_COST
                self.probe_speed_researched = True  # Mark upgrade as researched
                print("Probe Speed Upgrade Researched!")
                return True  # Research successful
        return False  # Research failed or already done

    def build_research_lab(self):
        if (self.minerals >= RESEARCH_LAB_BUILD_COST["minerals"] and
            self.gases >= RESEARCH_LAB_BUILD_COST["gases"]):
            self.minerals -= RESEARCH_LAB_BUILD_COST["minerals"]
            self.gases -= RESEARCH_LAB_BUILD_COST["gases"]
            self.research_labs += 1
            print("Research Lab Built!")
            return True
        return False

    def update(self, probes):  # Pass probes list to colony update
        if not self.probe_speed_researched:  # Try to research speed upgrade first if not done
            self.research_probe_speed_upgrade()  # Colony attempts to research every frame it has resources

        if len(probes) < MAX_PROBES:  # Check probe limit
            if (self.minerals > PROBE_CONSTRUCTION_THRESHOLD and
                    self.gases > PROBE_CONSTRUCTION_THRESHOLD and
                    self.probe_construction_timer <= 0):  # Check timer

                new_probe = self.construct_probe()
                if new_probe:
                    probes.append(new_probe)  # Colony adds probe to the list
                    self.probe_construction_timer = REPLICATION_COOLDOWN_TIME  # Reset timer

        if self.probe_construction_timer > 0:
            self.probe_construction_timer -= 1

        self.research += self.research_labs * RESEARCH_LAB_RESEARCH_RATE

        # Automated Research Lab Construction Logic:
        if self.lab_construction_timer <= 0:  # Check lab construction timer
            if (self.minerals > RESEARCH_LAB_BUILD_COST["minerals"] + RESEARCH_LAB_BUILD_THRESHOLD and  # Check resource thresholds
                self.gases > RESEARCH_LAB_BUILD_COST["gases"] + RESEARCH_LAB_BUILD_THRESHOLD):  # Added threshold buffer

                if self.build_research_lab():  # Attempt to build lab
                    self.lab_construction_timer = REPLICATION_COOLDOWN_TIME * 2  # Longer cooldown for labs
                    print("Colony AI decided to build a Research Lab.")  # Feedback for automated build

        if self.lab_construction_timer > 0:
            self.lab_construction_timer -= 1

# --------------------------
# Probe Class
# --------------------------
class Probe:
    def __init__(self, x, y, stars, colony, speed=2):  # Add colony parameter and speed
        self.x = x
        self.y = y
        self.speed = speed  # Now probe speed is set during construction
        self.cargo = {"minerals": 0, "gases": 0, "energy": 0, "research": 0}
        self.target = None
        self.state = "idle"
        self.stars = stars
        self.colony = colony  # Store the colony reference
        self.is_mining = False
        self.max_cargo = {"minerals": 200, "gases": 200, "energy": 200, "research": 100}
        self.visited_stars = set()
        self.replication_cooldown = 0  # Initialize replication cooldown (still useful for other timed actions if needed later)

    def set_target(self, target, state):
        self.target = target
        self.state = state
        if isinstance(target, Star):
            print(f"Probe at ({self.x:.1f}, {self.y:.1f}) assigned to star at ({target.x:.1f}, {target.y:.1f}) for {state}")
        elif isinstance(target, Colony):
            print(f"Probe at ({self.x:.1f}, {self.y:.1f}) returning to colony.")

    def find_nearest_star(self, resource_type="any"):
        nearest_star = None
        nearest_distance = float('inf')

        if resource_type == "any":
            needed_resources = self.needs_resources()
            if needed_resources:
                for star in self.stars:
                    if star in self.visited_stars:
                        continue
                    for resource in needed_resources:
                        if resource != "research" and getattr(star, resource) > 0:
                            distance = math.hypot(star.x - self.x, star.y - self.y)
                            if distance < nearest_distance:
                                nearest_distance = distance
                                nearest_star = star
                            break
                if nearest_star:
                    self.visited_stars.add(nearest_star)

        elif resource_type == "research":
            for star in self.stars:
                if star in self.visited_stars:
                    continue
                if star.research > 0:
                    distance = math.hypot(star.x - self.x, star.y - self.y)
                    if distance < nearest_distance:
                        nearest_distance = distance
                        nearest_star = star
            if nearest_star:
                self.visited_stars.add(nearest_star)
        return nearest_star

    def needs_resources(self):
        needed = {}
        for resource, amount in self.cargo.items():
            if amount < self.max_cargo[resource]:
                needed[resource] = self.max_cargo[resource] - amount
        return needed

    def find_star_with_resource(self, resource):
        for star in self.stars:
            if star in self.visited_stars:
                continue
            if getattr(star, resource) > 0:
                self.visited_stars.add(star)
                return star
        return None

    def update(self):
        if self.replication_cooldown > 0:  # Decrement cooldown if active (can be used for other timed events later)
            self.replication_cooldown -= 1

        if self.target:
            dx = self.target.x - self.x
            dy = self.target.y - self.y
            distance = math.hypot(dx, dy)

            if distance > self.speed:
                dx, dy = dx / distance, dy / distance
                self.x += dx * self.speed
                self.y += dy * self.speed
                distance = math.hypot(self.target.x - self.x, self.target.y - self.y)

            if distance <= self.speed:
                if isinstance(self.target, Star):
                    if self.target.total_resources() > 0:
                        needed_resources = self.needs_resources()
                        if self.state == "traveling_to_star_for_research":
                            resource_to_mine = "research"
                        elif needed_resources:
                            resource_to_mine = next(iter(needed_resources))
                        else:
                            self.target = None
                            self.state = "idle"
                            self.set_target(self.colony, "returning_to_colony")
                            return

                        available_resources = getattr(self.target, resource_to_mine)
                        mining_amount = min(self.speed, self.max_cargo[resource_to_mine] - self.cargo[resource_to_mine], available_resources)
                        if mining_amount > 0:
                            mined_amount = self.target.mine_resource(resource_to_mine, mining_amount)
                            self.cargo[resource_to_mine] += mined_amount
                            print(f"Probe mined {mined_amount} {resource_to_mine} from star. Cargo: {self.cargo}")

                            if self.target.total_resources() <= 0:
                                print(f"Star at ({self.target.x:.1f}, {self.target.y:.1f}) is depleted.")
                                self.target = None
                                self.state = "idle"
                                self.set_target(self.find_nearest_star(), "traveling_to_star")
                                return
                        else:
                            star_coords_str = f"({self.target.x:.1f}, {self.target.y:.1f})"
                            print(f"Star at {star_coords_str} does not have enough {resource_to_mine} or cargo full. Only {available_resources} available. Cargo: {self.cargo}")
                            self.target = None
                            self.state = "idle"
                            self.set_target(self.find_nearest_star(), "traveling_to_star")
                            return

                    else:
                        print(f"Star at ({self.target.x:.1f}, {self.target.y:.1f}) is depleted.")
                        self.target = None
                        self.state = "idle"
                        self.set_target(self.find_nearest_star(), "traveling_to_star")
                        return

                elif isinstance(self.target, Colony):
                    self.target.deposit(int(self.cargo["minerals"]), int(self.cargo["gases"]), int(self.cargo["energy"]), int(self.cargo["research"]))
                    print(f"Probe delivered resources to colony: {self.cargo}")
                    self.cargo = {"minerals": 0, "gases": 0, "energy": 0, "research": 0}
                    self.target = None
                    self.state = "idle"
                    self.is_mining = False
                    self.visited_stars = set()

                elif isinstance(self.target, ExplorationTarget):
                    bonus = random.randint(20, 50)
                    self.target.colony.deposit(bonus, bonus, bonus)  # Use target.colony
                    print(f"Probe discovered an anomaly! Bonus resources: {bonus} of each type")
                    self.target = None
                    self.state = "idle"
                    self.is_mining = False

        else:
            needed_resources = self.needs_resources()
            if needed_resources and "research" not in needed_resources:
                for resource in needed_resources:
                    if resource != "research":
                        star = self.find_star_with_resource(resource)
                        if star:
                            self.set_target(star, "traveling_to_star")
                            return

            if self.cargo["research"] < self.max_cargo["research"]:
                research_star = self.find_nearest_star(resource_type="research")
                if research_star:
                    self.set_target(research_star, "traveling_to_star_for_research")
                    return

            self.set_target(self.find_nearest_star(), "traveling_to_star")
            return

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

    def deposit(self, minerals, gases, energy, research):
        if isinstance(self.target, Colony):
            self.target.deposit(minerals, gases, energy, research)

    def communicate(self, other_probes):
        for other_probe in other_probes:
            if other_probe != self:
                distance = math.hypot(self.x - other_probe.x, self.y - other_probe.y)
                if distance <= COMMUNICATION_RADIUS:
                    other_probe.visited_stars.update(self.visited_stars)
        pass

    def is_hovered(self, mouse_x, mouse_y, zoom_level, offset_x, offset_y):
        radius = 5 * zoom_level
        draw_x = int((self.x - offset_x) * zoom_level)
        draw_y = int((self.y - offset_y) * zoom_level)
        return (draw_x - radius <= mouse_x <= draw_x + radius) and (draw_y - radius <= mouse_y <= draw_y + radius)


class ExplorationTarget:
    def __init__(self, x, y, colony):  # Needs colony
        self.x = x
        self.y = y
        self.colony = colony  # Store the colony

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
    colony = Colony(WORLD_WIDTH // 2, WORLD_HEIGHT // 2, stars)  # Pass stars to colony
    probes = [Probe(WORLD_WIDTH // 2, WORLD_HEIGHT // 2, stars, colony)]  # Pass colony

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

        # Update, Replicate, Communicate:
        for probe in probes[:]:  # Update all probes
            probe.update()

        # Probe replication is now handled by the colony
        colony.update(probes)  # Colony updates and handles probe construction, passing the probes list

        probes = [probe for probe in probes if len(probes) <= MAX_PROBES]  # Still need to enforce probe limit
        # Communicate
        for i in range(len(probes)):
            probes[i].communicate(probes)

        screen.fill((0, 0, 20))

        for star in stars:
            star.draw(screen, offset_x, offset_y, zoom_level)
        for probe in probes:
            probe.draw(screen, offset_x, offset_y, zoom_level)

            if probe.is_hovered(mouse_x, mouse_y, zoom_level, offset_x, offset_y):
                tooltip_text = f"Status: {probe.state}, Cargo: {probe.cargo}, Speed: {probe.speed}"  # Added speed to tooltip
                tooltip_surface = font.render(tooltip_text, True, (255, 255, 255))
                screen.blit(tooltip_surface, (mouse_x + 10, mouse_y + 10))

        colony.draw(screen, offset_x, offset_y, zoom_level)

        resource_text = font.render(
            f"Colony: Min={colony.minerals}, Gas={colony.gases}, Energy={colony.energy}, Research={colony.research}",
            True,
            (255, 255, 255),
        )
        screen.blit(resource_text, (10, 10))

        probe_count_text = font.render(
            f"Probes: {len(probes)}, Labs: {colony.research_labs}", True, (255, 255, 255)
        )
        screen.blit(probe_count_text, (10, 40))

        # Display upgrade status
        upgrade_text = font.render(
            f"Probe Speed Upgrade: {'Researched' if colony.probe_speed_researched else 'Not Researched'} (Cost: {PROBE_SPEED_UPGRADE_RESEARCH_COST} Research)",
            True,
            (255, 255, 255),
        )
        screen.blit(upgrade_text, (10, 70))  # Display below probe count

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()