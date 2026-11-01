import pygame as pg
from math import sin, cos, pi, atan2, degrees, radians, exp
from random import uniform
from os import path
from enum import Enum

from src.particle import Particle

vec = pg.math.Vector2


# viewing angle of each kart frame in deg: 0 = behind, 90 = side (index 7), 180 = front
KART_FRAME_ANGLES = [i * 90 / 7 for i in range(8)] + [90 + i * 22.5 for i in range(1, 5)]
MAX_STEER_FRAMES = 5  # frames the kart turns visually at full steering
STEER_FRAME_ANGLE = radians(KART_FRAME_ANGLES[1])  # yaw per steering frame


def get_kart_frame(images, flipped_images, yaw):
    # yaw in rad, positive = kart turned right relative to the view direction
    yaw_degrees = (degrees(yaw) + 180) % 360 - 180  # -180..180
    view_angle = abs(yaw_degrees)
    index = min(range(len(KART_FRAME_ANGLES)),
                key=lambda i: abs(KART_FRAME_ANGLES[i] - view_angle))
    return images[index] if yaw_degrees >= 0 else flipped_images[index]


class Direction(Enum):
    LEFT = 0
    RIGHT = 1
        

class Billboard(pg.sprite.Sprite):
    # static world sprite from a Tiled object, image = assets/<name>.png
    base_images = {}  # name -> surface
    scaled_images = {}  # (name, width) -> surface


    def __init__(self, game, tiled_object):
        super().__init__(game.billboards)
        self.game = game
        self.name = tiled_object.name
        # ground point = center of the object rect
        self.map_pos = vec(tiled_object.x + tiled_object.width / 2,
                           tiled_object.y + tiled_object.height / 2)
        self.world_width = tiled_object.width  # size on the map, set in Tiled

        if self.name not in Billboard.base_images:
            Billboard.base_images[self.name] = pg.image.load(
                path.join(game.assets_folder, f"{self.name}.png")).convert_alpha()
        self.base_image = Billboard.base_images[self.name]
        self.image = self.base_image
        self.rect = self.image.get_rect()
        self.depth = 0
        self.visible = False


    def get_scaled_image(self, width):
        key = (id(self.base_image), width)
        if key not in Billboard.scaled_images:
            aspect = self.base_image.get_height() / self.base_image.get_width()
            height = max(1, round(width * aspect))
            Billboard.scaled_images[key] = pg.transform.scale(self.base_image, (width, height))
        return Billboard.scaled_images[key]


    def update(self, dt):
        pass  # static by default, moving subclasses override this


    def project(self):
        # world -> screen, call after the camera moved
        mode7 = self.game.map
        camera = self.game.camera
        if camera.is_locked_on(self):
            # fixed kart spot, no jitter
            self.image = self.base_image
            self.depth = mode7.kart_ground_distance()
            self.visible = True
            return
        screen_rect = self.game.game_screen_rect
        horizon_offset = int(screen_rect.h * self.game.config["Visuals.horizon"])

        relative = self.map_pos - camera.pos

        forward_dir = camera.forward
        right_dir = vec(-forward_dir.y, forward_dir.x)
        forward = relative.dot(forward_dir)
        lateral = relative.dot(right_dir)
        self.depth = forward

        # inverse of render_mode7: distance along frustum edge -> screen row
        frustum_dist = forward / cos(mode7.fov_half)
        if frustum_dist <= mode7.near:
            self.visible = False
            return
        depth = (mode7.far - mode7.near) / (frustum_dist - mode7.near)
        ground_y = depth * screen_rect.h + horizon_offset
        row_width = 2 * frustum_dist * sin(mode7.fov_half)  # world units across screen
        screen_x = (lateral / row_width + 0.5) * screen_rect.w
        scale = screen_rect.w / row_width

        width = max(1, int(self.world_width * scale))
        if width > screen_rect.w * 2:  # too close, also keeps the cache small
            self.visible = False
            return
        self.image = self.get_scaled_image(width)
        self.rect = self.image.get_rect(midbottom=(screen_x, ground_y))
        self.visible = self.rect.colliderect(screen_rect)


    def draw(self, screen):
        if self.visible:
            screen.blit(self.image, self.rect)


class Kart(Billboard):
    # billboard using a kart sheet, needs angle, steer_yaw and map_pos

    def set_sheet(self, kart_name):
        self.images = self.game.kart_images[kart_name]
        self.images_flipped = self.game.kart_images_flipped[kart_name]
        self.base_image = self.images[0]


    @property
    def world_width(self):
        # world size that projects to the native sprite width at kart distance
        mode7 = self.game.map
        screen_w = self.game.game_screen_rect.w
        frustum_dist = mode7.kart_ground_distance() / cos(mode7.fov_half)
        row_width = 2 * frustum_dist * sin(mode7.fov_half)
        return self.base_image.get_width() * row_width / screen_w


    def project(self):
        # pick the frame from viewing angle + steering, then project as usual
        camera = self.game.camera
        to_kart = self.map_pos - camera.pos
        if to_kart.length_squared() > 0:
            view_angle = atan2(to_kart.y, to_kart.x)
        else:
            view_angle = camera.angle
        yaw = self.angle - view_angle + self.steer_yaw
        self.base_image = get_kart_frame(self.images, self.images_flipped, yaw)
        super().project()



class PathFollower(Kart):
    # AI kart that steers along a closed polygon (see Nature of Code path following)
    def __init__(self, game, path_points, kart_name, start_pos, start_angle):
        pg.sprite.Sprite.__init__(self, game.billboards)
        self.game = game
        self.name = kart_name
        self.set_sheet(kart_name)
        self.image = self.base_image
        self.rect = self.image.get_rect()
        self.depth = 0
        self.visible = False

        self.path_points = [vec(point) for point in path_points]
        self.path_radius = game.config["Gameplay.ai_path_radius"]       # px, no steering while inside
        # player's terminal speed on road: v = friction * (v + speed / FPS)
        friction = game.config["Gameplay.friction"]
        player_top_speed = friction * game.player.speed / game.config["Video.fps"] / (1 - friction)
        speed_factor = game.config["Gameplay.ai_speed_factor"]
        self.base_max_speed = player_top_speed * speed_factor
        self.max_speed = self.base_max_speed
        # force stays tied to base speed so handling doesn't change with variance
        self.max_force = game.config["Gameplay.ai_max_force"] * self.base_max_speed

        # speed variance: ease toward a random target that changes every few seconds
        self.speed_variance = game.config["Gameplay.ai_speed_variance"]
        self.speed_interval_min = game.config["Gameplay.ai_speed_interval_min"]
        self.speed_interval_max = game.config["Gameplay.ai_speed_interval_max"]
        self.speed_smoothing = game.config["Gameplay.ai_speed_smoothing"]
        self.variance_factor = 1.0
        self.target_variance_factor = 1.0
        self.time_until_variance_change = 0.0
        self.look_ahead_time = game.config["Gameplay.ai_look_ahead_time"]  # seconds
        self.steer_response_time = game.config["Gameplay.ai_steer_response_time"]
        self.separation_distance = game.config["Gameplay.ai_separation_distance"]  # in kart widths
        self.separation_weight = game.config["Gameplay.ai_separation_weight"]   # relative to path following
        self.target_ahead = game.config["Gameplay.ai_target_ahead"]      # px along the path

        self.map_pos = vec(start_pos)
        self.vel = vec()  # standing on the grid until the race starts
        self.acc = vec()

        self.angle = start_angle
        self.steer_yaw = 0.0
        self.turn_rate = 0.0  # rad/s, smoothed
        # player's turn rate at top speed -> full steering frames
        self.max_turn_rate = game.config["Gameplay.turn_force_fast"] * player_top_speed


    def get_normal_point(self, point, segment_start, segment_end):
        # closest point to 'point' on the segment
        segment = segment_end - segment_start
        projection = (point - segment_start).dot(segment) / segment.length_squared()
        projection = max(0.0, min(1.0, projection))
        return segment_start + segment * projection


    def follow_path(self):
        predicted_pos = self.map_pos + self.vel * self.look_ahead_time
        closest_distance = float("inf")
        target = None
        point_count = len(self.path_points)
        for i in range(point_count):
            segment_start = self.path_points[i]
            segment_end = self.path_points[(i + 1) % point_count]
            normal_point = self.get_normal_point(predicted_pos, segment_start, segment_end)
            distance = predicted_pos.distance_to(normal_point)
            if distance < closest_distance:
                closest_distance = distance
                segment_direction = (segment_end - segment_start).normalize()
                target = normal_point + segment_direction * self.target_ahead

        if closest_distance > self.path_radius:
            self.seek(target)


    def seek(self, target):
        desired = target - self.map_pos
        if desired.length_squared() == 0:
            return
        desired.scale_to_length(self.max_speed)
        steer = (desired - self.vel) / self.steer_response_time
        if steer.length() > self.max_force:
            steer.scale_to_length(self.max_force)
        self.acc += steer


    def separate(self):
        # steer away from karts that are too close (Nature of Code separation)
        min_distance = self.separation_distance * self.world_width
        push_sum = vec()
        count = 0
        for other in self.game.billboards:
            if other is self or not isinstance(other, Kart):
                continue
            offset = self.map_pos - other.map_pos
            distance = offset.length()
            if 0 < distance < min_distance:
                push_sum += offset.normalize() / distance  # closer -> stronger
                count += 1
        if count == 0:
            return
        desired = push_sum / count
        desired.scale_to_length(self.max_speed)
        steer = (desired - self.vel) / self.steer_response_time
        if steer.length() > self.max_force:
            steer.scale_to_length(self.max_force)
        self.acc += steer * self.separation_weight


    def accelerate(self):
        # throttle along the heading, steering alone doesn't speed up the kart
        if self.vel.length() < self.max_speed:
            heading = vec(cos(self.angle), sin(self.angle))
            self.acc += heading * self.max_force


    def update_speed_variance(self, dt):
        self.time_until_variance_change -= dt
        if self.time_until_variance_change <= 0:
            self.target_variance_factor = 1.0 + uniform(-self.speed_variance,
                                                        self.speed_variance)
            self.time_until_variance_change = uniform(self.speed_interval_min,
                                                      self.speed_interval_max)
        # framerate independent exponential smoothing
        blend = 1 - exp(-self.speed_smoothing * dt)
        self.variance_factor += (self.target_variance_factor - self.variance_factor) * blend
        self.max_speed = self.base_max_speed * self.variance_factor


    def update(self, dt):
        if self.game.started:
            self.update_speed_variance(dt)
            self.follow_path()
            self.separate()
            self.accelerate()
            self.vel += self.acc * dt
            if self.vel.length() > self.max_speed:
                self.vel.scale_to_length(self.max_speed)

            self.map_pos += self.vel * dt
            self.acc *= 0
            self.update_steering(dt)


    def update_steering(self, dt):
        if dt <= 0 or self.vel.length_squared() == 0:
            return
        new_angle = atan2(self.vel.y, self.vel.x)
        angle_change = (new_angle - self.angle + pi) % (2 * pi) - pi
        self.angle = new_angle
        # low-pass filter so small corrections don't flicker
        smoothing = min(1.0, dt * 10)
        self.turn_rate += (angle_change / dt - self.turn_rate) * smoothing
        steer_frames = min(MAX_STEER_FRAMES,
                           round(abs(self.turn_rate) / self.max_turn_rate * MAX_STEER_FRAMES))
        steer_sign = 1 if self.turn_rate > 0 else -1
        self.steer_yaw = steer_sign * steer_frames * STEER_FRAME_ANGLE



class Player(Kart):
    def __init__(self, game, kart_name):
        pg.sprite.Sprite.__init__(self, game.billboards)
        self.game = game
        self.name = "player"
        self.depth = 0
        self.visible = True

        self.angle = -1.54  # TODO should depend on teh track's starting line orientation
        self.acc = vec()
        self.vel = vec()
        self.pos = vec(2892.8, 1216.0)  # fallback if course has no start positions
        self.speed = 1800
        self.last_road_pos = vec(0, 0)  # last known position on road
        
        self.set_sheet(kart_name)  # base_image = current unscaled frame
        self.steer_yaw = 0.0  # visual turn from steering in rad, positive = right
        self.image = self.base_image
        self.rect = self.image.get_rect()
        self.rect.topleft = (84, 84)
        
        self.time_passed = 0 # seconds from the start of the game
        self.steer_time = 0 # seconds the player is pressing a direction
        self.lastdir: Direction = Direction.LEFT
        self.moving = 1 # 1 forward, -1 backwards
        self.dust_timer = 0
        self.dirt_timer = 0
        
    
    def update(self, dt):
        self.time_passed += dt

        keys = pg.key.get_pressed()
        
        if not self.game.started:
            if keys[pg.K_w]:
                self.dust_timer += dt
                if self.dust_timer >= 0.3:
                    # create two particles (left and right)
                    Particle(
                        self.game, 
                        self.rect.bottomright, 
                        images=[self.game.cloud_image],
                        colors=[pg.Color('white')],
                        vel=vec(1, 0),
                        random_angle=20,
                        vanish_speed=20,
                        end_size=1.4
                        )
                    Particle(
                        self.game, 
                        self.rect.bottomleft, 
                        images=[self.game.cloud_image],
                        colors=[pg.Color('white')],
                        vel=vec(-1, 0),
                        random_angle=20,
                        vanish_speed=20,
                        end_size=1.4
                        )
                    self.dust_timer = 0
            
        else:
            if self.moving == 1:
                turn_force = 0.00625 # how much the angle changes when turning
            else:
                turn_force = 0.015625
            steer_anim_speed = 10 # turning animation speed
            
            current_speed = self.vel.length()
            
            # steer
            steer_frames = min(MAX_STEER_FRAMES - 1, int(self.steer_time * steer_anim_speed))

            if keys[pg.K_a]:
                # turning left
                if self.lastdir == Direction.RIGHT:
                    self.steer_time = 0
                self.steer_time += dt
                self.angle -= turn_force * dt * current_speed * self.moving
                steer_frames += 1  # first turning frame right away
                self.lastdir = Direction.LEFT
            elif keys[pg.K_d]:
                # turning right
                if self.lastdir == Direction.LEFT:
                    self.steer_time = 0
                self.steer_time += dt
                self.angle += turn_force * dt * current_speed * self.moving
                steer_frames += 1
                self.lastdir = Direction.RIGHT
            else:
                self.steer_time -= dt

            # reversing turns the kart the other way
            steer_sign = 1 if self.lastdir == Direction.RIGHT else -1
            self.steer_yaw = steer_sign * self.moving * steer_frames * STEER_FRAME_ANGLE
            
            # limit the steer time between 0 and the maximum image index
            self.steer_time = max(min(self.steer_time, 0.6), 0)
                
            # move forward or backwards
            if keys[pg.K_w]:
                self.moving = 1
                self.acc.x = self.speed
                self.acc.y = self.speed
            elif keys[pg.K_s]:
                self.moving = -1
                self.acc.x = self.speed * -0.4
                self.acc.y = self.speed * -0.4

            # ground tiles affect acceleration
            ground_speed = self.game.ground_speed_at(self.pos)
            #self.game.debug_values['ground_speed'] = f'{ground_speed:.1f}'
            if ground_speed == 1.0:
                # store position if ground_speed is 1 (= on road)
                self.last_road_pos.x = self.pos.x
                self.last_road_pos.y = self.pos.y
            self.acc *= ground_speed
    
            self.vel.x += self.acc.x * cos(self.angle) * dt
            self.vel.y += self.acc.y * sin(self.angle) * dt
            self.pos += self.vel * dt
            
            self.acc *= 0
            # apply friction
            self.vel *= 0.9
    
            
            # jiggle texture up and down
            if int(self.time_passed * self.game.config["Visuals.kart_jiggle_speed"]) % 2 == 0 and current_speed >= 32:
                self.rect.top = 85
            else:
                self.rect.top = 84
                
            
            # create dust clouds when steering
            self.dust_timer += dt
            if self.dust_timer >= 0.2:
                if self.lastdir == Direction.RIGHT:
                    v = vec(3, 0) * self.moving
                elif self.lastdir == Direction.LEFT:
                    v = vec(-3, 0) * self.moving
                if self.steer_time >= 0.3 and current_speed > 128:
                    if self.moving == 1:
                        p = Particle(
                            self.game, 
                            self.rect.midbottom, 
                            images=[self.game.cloud_image],
                            colors=[pg.Color('white')],
                            vel=v,
                            random_angle=30,
                            vanish_speed=20,
                            end_size=1.4
                            )
                        p.add_force(vec(0, 1), 10)
                    else:
                        p = Particle(
                            self.game, 
                            self.rect.midbottom, 
                            images=[self.game.cloud_image],
                            colors=[pg.Color('white')],
                            vel=v, 
                            random_angle=30,
                            vanish_speed=20,
                            end_size=0.9
                            )
                        p.add_force(vec(0, -2), 10)
                    
                self.dust_timer = 0


            # create dirt/grass particles when offroad
            if ground_speed < 1.0:
                # TODO check for different ground tiles
                if self.vel.length_squared() > 0.0001:
                    self.dirt_timer += dt
                if self.dirt_timer >= 0.2:
                    self.dirt_timer = 0
                    # create two particles (left and right)
                    Particle(
                        self.game, 
                        self.rect.bottomright, 
                        images=[self.game.dirt_image],
                        colors=[pg.Color('white')],
                        vel=vec(1, 0),
                        random_angle=20,
                        vanish_speed=20,
                        end_size=1.4
                        )
                    Particle(
                        self.game, 
                        self.rect.bottomleft, 
                        images=[self.game.dirt_image],
                        colors=[pg.Color('white')],
                        vel=vec(-1, 0),
                        random_angle=20,
                        vanish_speed=20,
                        end_size=1.4
                        )


        # check against the killzone
        if self.game.check_in_killzone(self.pos):
            # warp back to last known road position
            # TODO: trigger event with animation and stuff
            print("Dead")
            self.pos.x = self.last_road_pos.x
            self.pos.y = self.last_road_pos.y


    @property
    def map_pos(self):
        return self.pos



class TrafficLight(pg.sprite.Sprite):
    def __init__(self, game, pos):
        super().__init__(game.all_sprites)
        self.game = game
        self.images = [game.traffic_light_images.subsurface((i * 24, 0, 24, 32)) for i in range(5)]
        self.image = self.images[0]
        self.rect = self.image.get_rect()
        self.rect.center = pos
        self.done = False
        self.timer = 0
        self.img_index = 0
        
    
    def update(self, dt):
        self.timer += dt
        if self.timer >= 1:
            self.timer = 0
            self.img_index += 1
            if self.img_index == 4:
                self.done = True
            try:
                self.image = self.images[self.img_index]
            except:
                self.kill()
        

    def draw(self, screen):
        screen.blit(self.image, self.rect)