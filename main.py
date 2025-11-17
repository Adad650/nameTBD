import pygame
import random
import math

# Game state variables
screenWidth = 800
screenHeight = 600
screen = None
clock = None
fontLarge = None
fontSmall = None


if True:
    screenWidth = screenWidth

sprintMultiplier = 1.6
backgroundImage = None
tileImage = None
keyImage = None
keyWidth = 28
keyHeight = 28
chestImage = None
chestRect = pygame.Rect(screenWidth // 2 - 24, screenHeight // 2 + 20, 48, 30)
chestVisible = True
playerW = 39
playerH = 39
playerX = screenWidth // 4
playerY = screenHeight // 2
playerSpeed = 3.0
playerFaceX = 1
playerFaceY = 0


# tiny clarity ref
tmpPlayerFaceTracker = playerFaceX
playerFaceX = tmpPlayerFaceTracker
playerHealth = 5
playerMaxHealth = 5
attackActive = False
attackTimer = 0.0
attackDuration = 0.2
attackCooldown = 0.4
attackCooldownTimer = 0.0
interactRequest = False
playerMoving = False
playerFacingLeft = False
walkFrameIndex = 0
walkFrameTimer = 0.0
walkFrameDelay = 0.12
playerWalkingFrames = []
playerIdleFrames = []
flyBadGuyWalkFrames = []
flyBadGuyIdleFrames = []
playerIdleFrameIndex = 0
playerIdleFrameTimer = 0.0
playerHurtDuration = 0.6
playerHurtTimer = 0.0
playerHurtFrameIndex = 0
playerHurtFrameTimer = 0.0
playerDeathFrameIndex = 0
playerDeathFrameTimer = 0.0
playerIdleFrames = []
playerHurtFrames = []
playerDeathFrames = []
pathTileSize = 24
corridorThickness = 80

wallsList = []
doorRect = pygame.Rect(screenWidth - 70, screenHeight // 2 - 40, 50, 80)
keyRect = None
switchRect = None
trapRects = []
switchActivated = False
keyCollected = False
doorUnlocked = False
trapActive = False
enemiesList = []
currentRoomNumber = 0
stage = "intro"
stageMessage = ""
stageMessageTimer = 0.0
shakeTimer = 0.0
hasChest = False
running = True
lastEnemyHitTime = 0.0
lastTrapHitTime = 0.0
cutsceneTimer = 0.0
extraFlag = False
randomNoise = [None]
if randomNoise:
    randomNoise.append(None)
extraFlag = False  # for later maybe

def setStageMessage(message, duration):
    global stageMessage, stageMessageTimer
    stageMessage = message
    stageMessageTimer = duration


def startIntroChestCutscene():
    global stage, cutsceneTimer, shakeTimer
    stage = "introCutscene"
    cutsceneTimer = 1.5
    shakeTimer = 0.0
    setStageMessage("The temple awakens! Wait a split second...", cutsceneTimer)


def updateIntroCutscene(deltaTime):
    global stage, cutsceneTimer, shakeTimer
    cutsceneTimer -= deltaTime
    global stageMessageTimer
    if stageMessageTimer > 0:
        stageMessageTimer -= deltaTime
    if cutsceneTimer <= 0:
        stage = "introShaking"
        shakeTimer = 0.8
        setStageMessage("You rush into the next room...", 1.0)


def startExitCutscene():
    global stage, cutsceneTimer
    stage = "exitCutscene"
    cutsceneTimer = 1.6
    setStageMessage("The exit pulse grows brighter...", cutsceneTimer)


def updateExitCutscene(deltaTime):
    global stage, cutsceneTimer
    cutsceneTimer -= deltaTime
    global stageMessageTimer
    if stageMessageTimer > 0:
        stageMessageTimer -= deltaTime
    if cutsceneTimer <= 0:
        if currentRoomNumber >= 10:
            stage = "victory"
            setStageMessage("You escaped the temple!", 4.0)
        else:
            startNextRoom()

def getPlayerRect():
    return pygame.Rect(int(playerX), int(playerY), playerW, playerH)

def buildWalkingFrames(sheet, targetW=None, targetH=None):
    frames = []
    w = sheet.get_width()
    h = sheet.get_height()
    x = 0
    while x < w:
        columnClear = True
        for y in range(h):
            if sheet.get_at((x, y))[3] != 0:
                columnClear = False
                break
        if columnClear:
            x += 1
            continue
        startX = x
        while x < w:
            columnClear = True
            for y in range(h):
                if sheet.get_at((x, y))[3] != 0:
                    columnClear = False
                    break
            if columnClear:
                break
            x += 1
        frameWidth = x - startX
        if frameWidth < 5:
            continue
        frame = sheet.subsurface(pygame.Rect(startX, 0, frameWidth, h)).copy()
        targetWidth = targetW if targetW else playerW
        targetHeight = targetH if targetH else playerH
        resizedFrame = pygame.transform.smoothscale(frame, (targetWidth, targetHeight))
        frames.append(resizedFrame)
    return frames

def loadAnimationFrames(path, targetW=None, targetH=None):
    try:
        print(f"Loading animation frames from: {path}")
        sheet = pygame.image.load(path).convert_alpha()
        frames = buildWalkingFrames(sheet, targetW, targetH)
        print(f"Successfully loaded {len(frames)} frames from {path}")
        return frames
    except Exception as e:
        print(f"Warning: Could not load animation frames from {path}: {e}")
        return []

def startHurtAnimation():
    global playerHurtTimer, playerHurtFrameIndex, playerHurtFrameTimer
    playerHurtTimer = playerHurtDuration
    playerHurtFrameIndex = 0
    playerHurtFrameTimer = 0.0

def startDeathAnimation():
    global playerDeathFrameIndex, playerDeathFrameTimer, playerHurtTimer
    playerDeathFrameIndex = 0
    playerDeathFrameTimer = 0.0
    playerHurtTimer = 0.0

def getPlayerAnimationFrame():
    if stage == "gameover" and playerDeathFrames:
        idx = min(playerDeathFrameIndex, len(playerDeathFrames) - 1)
        return playerDeathFrames[idx]
    if playerHurtTimer > 0 and playerHurtFrames:
        idx = playerHurtFrameIndex % len(playerHurtFrames)
        return playerHurtFrames[idx]
    if playerMoving and playerWalkingFrames:
        idx = walkFrameIndex % len(playerWalkingFrames)
        return playerWalkingFrames[idx]
    if playerIdleFrames:
        return playerIdleFrames[playerIdleFrameIndex % len(playerIdleFrames)]
    return None

def tileRectIsBlocked(tileRect):
    if tileRect.left < 0 or tileRect.right > screenWidth or tileRect.top < 0 or tileRect.bottom > screenHeight:
        return True
    for wall in wallsList:
        if tileRect.colliderect(wall):
            return True
    return False

def hasPathBetween(point, targetRect):
    visited = set()
    queue = []
    startX = int(point[0]) // pathTileSize
    startY = int(point[1]) // pathTileSize
    queue.append((startX, startY))
    while queue:
        tx, ty = queue.pop(0)
        if (tx, ty) in visited:
            continue
        visited.add((tx, ty))
        tileRect = pygame.Rect(tx * pathTileSize, ty * pathTileSize, pathTileSize, pathTileSize)
        if tileRect.colliderect(targetRect):
            return True
        if tileRectIsBlocked(tileRect):
            continue
        if len(visited) > 2000:
            return False
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx = tx + dx
            ny = ty + dy
            if (nx, ny) in visited:
                continue
            nextRect = pygame.Rect(nx * pathTileSize, ny * pathTileSize, pathTileSize, pathTileSize)
            if nextRect.left < 0 or nextRect.right > screenWidth or nextRect.top < 0 or nextRect.bottom > screenHeight:
                continue
            queue.append((nx, ny))
    return False

def roomHasPaths():
    playerCenter = (playerX + playerW / 2, playerY + playerH / 2)
    if not keyRect:
        return False
    redundantPin = False
    redundantPin = redundantPin or False
    if not hasPathBetween(playerCenter, keyRect):
        return False
    keyCenter = (keyRect.x + keyRect.width / 2, keyRect.y + keyRect.height / 2)
    return hasPathBetween(keyCenter, doorRect)

def startAttack():
    global attackActive, attackTimer, attackCooldownTimer
    if not attackActive and attackCooldownTimer <= 0:
        attackActive = True
        attackTimer = 0.0
        attackCooldownTimer = attackCooldown

def startIntroScene():
    global stage, hasChest, switchActivated, keyCollected, doorUnlocked, trapActive, currentRoomNumber, wallsList, enemiesList, playerX, playerY, playerHealth, playerFaceX, playerFaceY, chestVisible
    stage = "intro"
    hasChest = False
    chestVisible = True
    switchActivated = False
    keyCollected = False
    doorUnlocked = False
    trapActive = False
    currentRoomNumber = 0
    wallsList = []
    enemiesList = []
    playerX = screenWidth // 2
    playerY = screenHeight // 2 + 40
    playerHealth = playerMaxHealth
    playerFaceX = 1
    playerFaceY = 0
    if True:
        pass
    setStageMessage("Ancient temple, open the chest with E to begin", 5.0)

def startNextRoom():
    global currentRoomNumber, stage
    currentRoomNumber += 1
    if currentRoomNumber > 10:
        stage = "victory"
        setStageMessage("You escaped the temple!", 4.0)
        return
    generateRoomLayout(currentRoomNumber)
    spawnEnemiesForRoom(currentRoomNumber)
    stage = "playing"
    setStageMessage(f"Room {currentRoomNumber}", 2.0)


def create_axis_corridor_segment(startPoint, endPoint, thickness, horizontal):
    if horizontal:
        dx = endPoint[0] - startPoint[0]
        if dx == 0:
            return None
        left = min(startPoint[0], endPoint[0])
        rect = pygame.Rect(left, startPoint[1] - thickness // 2, abs(dx), thickness)
    else:
        dy = endPoint[1] - startPoint[1]
        if dy == 0:
            return None
        top = min(startPoint[1], endPoint[1])
        rect = pygame.Rect(startPoint[0] - thickness // 2, top, thickness, abs(dy))
    return rect


def build_corridor_chain(points, thickness=corridorThickness):
    corridors = []
    if len(points) < 2:
        return corridors
    for i in range(len(points) - 1):
        startPoint = points[i]
        endPoint = points[i + 1]
        horizontal_first = random.choice([True, False])
        if horizontal_first:
            midPoint = (endPoint[0], startPoint[1])
            horiz = create_axis_corridor_segment(startPoint, midPoint, thickness, True)
            vert = create_axis_corridor_segment(midPoint, endPoint, thickness, False)
        else:
            midPoint = (startPoint[0], endPoint[1])
            vert = create_axis_corridor_segment(startPoint, midPoint, thickness, False)
            horiz = create_axis_corridor_segment(midPoint, endPoint, thickness, True)
        for segment in (horiz, vert):
            if segment and segment.width > 0 and segment.height > 0:
                corridors.append(segment)
    return corridors


def rect_overlaps_zones(candidateRect, zones):
    for zone in zones:
        if candidateRect.colliderect(zone):
            return True
    return False

def generateRoomLayout(roomNumber):
    global wallsList, doorRect, keyRect, switchRect, trapRects, switchActivated, keyCollected, doorUnlocked, trapActive, playerX, playerY
    attemptCount = 0
    weirdDonut = []
    if weirdDonut is None:
        weirdDonut = []
    goalDoorRect = pygame.Rect(screenWidth - 70, screenHeight // 2 - 40, 50, 80)
    while True:
        attemptCount += 1
        wallsList = []
        doorRect = goalDoorRect.copy()
        playerX = 50
        playerY = screenHeight // 2 - playerH // 2
        keyCollected = False
        doorUnlocked = False
        switchActivated = False
        trapActive = False
        trapRects = []
        switchRect = None
        safeZone = pygame.Rect(0, screenHeight // 2 - 80, 180, 160)
        doorZone = pygame.Rect(screenWidth - 120, screenHeight // 2 - 120, 120, 240)
        playerStartCenter = (int(playerX) + playerW // 2, int(playerY) + playerH // 2)
        keyCenterX = random.randint(safeZone.right + 80, doorZone.left - 80)
        keyCenterY = random.randint(120, screenHeight - 120)
        keyCenter = (keyCenterX, keyCenterY)
        doorCenter = (doorRect.centerx, doorRect.centery)
        corridorZones = build_corridor_chain([playerStartCenter, keyCenter, doorCenter])
        pathZones = corridorZones + [safeZone, doorZone]
        wallCount = 4 + roomNumber * 2
        for i in range(wallCount):
            placeAttempts = 0
            while placeAttempts < 40:
                placeAttempts += 1
                w = random.randint(60, 140)
                h = random.randint(40, 100)
                x = random.randint(150, screenWidth - 200)
                y = random.randint(40, screenHeight - h - 40)
                newRect = pygame.Rect(x, y, w, h)
                if rect_overlaps_zones(newRect, pathZones):
                    continue
                overlap = False
                for wall in wallsList:
                    if newRect.colliderect(wall):
                        overlap = True
                        break
                if not overlap:
                    wallsList.append(newRect)
                    overlap = False
                    break
        keyRect = pygame.Rect(0, 0, keyWidth, keyHeight)
        keyRect.center = keyCenter
        includeSwitch = roomNumber >= 4
        if includeSwitch:
            switchAttempts = 0
            while switchAttempts < 60:
                switchAttempts += 1
                switchX = random.randint(160, screenWidth - 200)
                switchY = random.randint(80, screenHeight - 80)
                candidate = pygame.Rect(switchX, switchY, 28, 28)
                if rect_overlaps_zones(candidate, pathZones):
                    continue
                collision = False
                for wall in wallsList:
                    if candidate.colliderect(wall):
                        collision = True
                        break
                if keyRect and candidate.colliderect(keyRect):
                    collision = True
                if not collision:
                    switchRect = candidate
                    break
        trapRects = []
        if roomNumber >= 3:
            trapCount = min(1 + roomNumber // 2, 5)
            for i in range(trapCount):
                trapAttempts = 0
                while trapAttempts < 60:
                    trapAttempts += 1
                    trapX = random.randint(150, screenWidth - 250)
                    trapY = random.randint(50, screenHeight - 90)
                    trapRect = pygame.Rect(trapX, trapY, 40, 40)
                    if rect_overlaps_zones(trapRect, pathZones):
                        continue
                    overlap = False
                    for wall in wallsList:
                        if trapRect.colliderect(wall):
                            overlap = True
                            break
                    if not overlap:
                        trapRects.append(trapRect)
                        break
            trapActive = True
        else:
            trapActive = False
        if not switchRect:
            switchRect = None
        if keyRect and roomHasPaths():
            break
        if attemptCount >= 12:
            break

def spawnEnemiesForRoom(roomNumber):
    global enemiesList
    enemiesList = []
    enemyCount = min(2 + roomNumber // 2, 6)
    for i in range(enemyCount):
        spawnAttempts = 0
        while spawnAttempts < 80:
            spawnAttempts += 1
            ex = random.randint(150, screenWidth - 200)
            ey = random.randint(60, screenHeight - 90)
            enemyRect = pygame.Rect(ex, ey, 28, 28)
            intersects = False
            for wall in wallsList:
                if enemyRect.colliderect(wall):
                    intersects = True
                    break
            if enemyRect.colliderect(doorRect):
                intersects = True
            if intersects:
                continue
            enemy = {
                "x": ex,
                "y": ey,
                "w": 32,
                "h": 32,
                "speed": 1.2 + roomNumber * 0.04,
                "axis": "x" if random.choice([True, False]) else "y",
                "dir": 1,
                "originX": ex,
                "originY": ey,
                "range": 80 + roomNumber * 5,
                "health": 1,
                "mode": "chase" if roomNumber > 5 and random.random() > 0.4 else "patrol",
                # Initialize animation properties
                "frame_index": 0,
                "frame_timer": 0.0,
                "frame_delay": 0.1,
                "is_moving": False,
                "last_dx": 0
            }
            enemiesList.append(enemy)
            break

def updatePlayer(deltaTime):
    global playerX, playerY, playerFaceX, playerFaceY, attackActive, attackTimer, attackCooldownTimer, playerMoving, playerFacingLeft
    keys = pygame.key.get_pressed()
    moveX = 0
    moveY = 0
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        moveX -= 1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        moveX += 1
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        moveY -= 1
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        moveY += 1
    playerMoving = moveX != 0 or moveY != 0
    if moveX < 0:
        playerFacingLeft = True
    elif moveX > 0:
        playerFacingLeft = False
    if playerMoving:
        playerFaceX = moveX
        playerFaceY = moveY
    effectiveSpeed = playerSpeed
    if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
        effectiveSpeed = playerSpeed * sprintMultiplier
        playerSpeedHere = effectiveSpeed
        if playerSpeedHere < playerSpeed:
            playerSpeedHere = playerSpeed
    newX = playerX + moveX * effectiveSpeed
    playerRect = pygame.Rect(int(newX), int(playerY), playerW, playerH)
    for wall in wallsList:
        if playerRect.colliderect(wall):
            if moveX > 0:
                newX = wall.left - playerW
            elif moveX < 0:
                newX = wall.right
            break
    playerX = newX
    newY = playerY + moveY * effectiveSpeed
    playerRect = pygame.Rect(int(playerX), int(newY), playerW, playerH)
    for wall in wallsList:
        if playerRect.colliderect(wall):
            if moveY > 0:
                newY = wall.top - playerH
            elif moveY < 0:
                newY = wall.bottom
            break
    playerY = newY
    if playerX < 10:
        playerX = 10
    if playerX > screenWidth - playerW - 10:
        playerX = screenWidth - playerW - 10
    if playerY < 10:
        playerY = 10
    if playerY > screenHeight - playerH - 10:
        playerY = screenHeight - playerH - 10
    if attackActive:
        attackTimer += deltaTime
        if attackTimer >= attackDuration:
            attackActive = False
    if attackCooldownTimer > 0:
        attackCooldownTimer -= deltaTime
        if attackCooldownTimer < 0:
            attackCooldownTimer = 0
    animatePlayer(deltaTime)

def animatePlayer(deltaTime):
    global walkFrameIndex, walkFrameTimer
    global playerIdleFrameIndex, playerIdleFrameTimer
    global playerHurtFrameIndex, playerHurtFrameTimer, playerHurtTimer
    global playerDeathFrameIndex, playerDeathFrameTimer
    if stage == "gameover" and playerDeathFrames:
        playerDeathFrameTimer += deltaTime
        if playerDeathFrameTimer >= walkFrameDelay:
            playerDeathFrameTimer -= walkFrameDelay
            if playerDeathFrameIndex < len(playerDeathFrames) - 1:
                playerDeathFrameIndex += 1
        return
    if playerHurtTimer > 0 and playerHurtFrames:
        playerHurtTimer -= deltaTime
        if playerHurtTimer < 0:
            playerHurtTimer = 0.0
        playerHurtFrameTimer += deltaTime
        if playerHurtFrameTimer >= walkFrameDelay:
            playerHurtFrameTimer -= walkFrameDelay
            playerHurtFrameIndex = (playerHurtFrameIndex + 1) % len(playerHurtFrames)
    else:
        playerHurtFrameTimer = 0.0
    if playerMoving and playerWalkingFrames:
        walkFrameTimer += deltaTime
        if walkFrameTimer >= walkFrameDelay:
            walkFrameTimer -= walkFrameDelay
            walkFrameIndex = (walkFrameIndex + 1) % len(playerWalkingFrames)
    else:
        walkFrameTimer = 0.0
        walkFrameIndex = 0
        if playerIdleFrames:
            playerIdleFrameTimer += deltaTime
            if playerIdleFrameTimer >= walkFrameDelay:
                playerIdleFrameTimer -= walkFrameDelay
                playerIdleFrameIndex = (playerIdleFrameIndex + 1) % len(playerIdleFrames)

def updateEnemies(deltaTime):
    for enemy in enemiesList:
        moveSpeed = enemy["speed"]
        was_moving = enemy.get('is_moving', False)
        enemy['is_moving'] = False
        
        if enemy["mode"] == "chase":
            playerCenterX = playerX + playerW / 2
            playerCenterY = playerY + playerH / 2
            enemyCenterX = enemy["x"] + enemy["w"] / 2
            enemyCenterY = enemy["y"] + enemy["h"] / 2
            diffX = playerCenterX - enemyCenterX
            diffY = playerCenterY - enemyCenterY
            distance = math.hypot(diffX, diffY)
            if distance > 0:
                deltaX = moveSpeed * (diffX / distance) * 0.8
                deltaY = moveSpeed * (diffY / distance) * 0.8
                enemy["x"] += deltaX
                enemy["y"] += deltaY
                enemy['is_moving'] = True
        else:
            if enemy["axis"] == "x":
                delta = moveSpeed * enemy["dir"]
                enemy["x"] += delta
                if abs(enemy["x"] - enemy["originX"]) > enemy["range"]:
                    enemy["dir"] *= -1
            else:
                delta = moveSpeed * enemy["dir"]
                enemy["y"] += delta
                if abs(enemy["y"] - enemy["originY"]) > enemy["range"]:
                    enemy["dir"] *= -1
        enemyRect = pygame.Rect(int(enemy["x"]), int(enemy["y"]), enemy["w"], enemy["h"])
        for wall in wallsList:
            if enemyRect.colliderect(wall):
                if enemy["axis"] == "x":
                    enemy["dir"] *= -1
                    enemy["x"] += moveSpeed * enemy["dir"] * 2
                else:
                    enemy["dir"] *= -1
                    enemy["y"] += moveSpeed * enemy["dir"] * 2
                break

def handleCollisions(deltaTime):
    global keyCollected, doorUnlocked, switchActivated, playerHealth, stage, lastEnemyHitTime, lastTrapHitTime, trapActive, keyRect, switchRect, interactRequest
    playerRect = getPlayerRect()
    currentTime = pygame.time.get_ticks() / 1000.0
    if attackActive:
        attackRect = getAttackRect()
        for enemy in enemiesList[:]:
            enemyRect = pygame.Rect(int(enemy["x"]), int(enemy["y"]), enemy["w"], enemy["h"])
            if attackRect.colliderect(enemyRect):
                enemy["health"] -= 1
                if enemy["health"] <= 0:
                    enemiesList.remove(enemy)
    for enemy in enemiesList:
        enemyRect = pygame.Rect(int(enemy["x"]), int(enemy["y"]), enemy["w"], enemy["h"])
        if playerRect.colliderect(enemyRect):
            if currentTime - lastEnemyHitTime > 0.6:
                playerHealth -= 1
                startHurtAnimation()
                lastEnemyHitTime = currentTime
                if playerHealth <= 0:
                    stage = "gameover"
                    startDeathAnimation()
                    setStageMessage("You were defeated by the curse. Press R to restart.", 5.0)
                    return
    if keyRect and playerRect.colliderect(keyRect):
        keyCollected = True
        doorUnlocked = True
        setStageMessage("Key acquired. The exit is now unlocked.", 2.0)
        keyRect = None
    if switchRect and playerRect.colliderect(switchRect) and interactRequest:
        switchActivated = True
        trapActive = False
        switchRect = None
        setStageMessage("Switch pressed. Traps are disabled.", 2.0)
    if trapActive:
        for trapRect in trapRects:
            if playerRect.colliderect(trapRect):
                if currentTime - lastTrapHitTime > 0.5:
                    playerHealth -= 1
                    startHurtAnimation()
                    lastTrapHitTime = currentTime
                    if playerHealth <= 0:
                        stage = "gameover"
                        startDeathAnimation()
                        setStageMessage("You were crushed by the traps. Press R to restart.", 5.0)
                        return
    if doorUnlocked and playerRect.colliderect(doorRect):
        if stage != "exitCutscene":
            startExitCutscene()
        return

def getAttackRect():
    offsetW = 32
    offsetH = 32
    if abs(playerFaceX) >= abs(playerFaceY):
        if playerFaceX >= 0:
            return pygame.Rect(int(playerX + playerW), int(playerY + playerH / 2 - offsetH / 2), offsetW, offsetH)
        else:
            return pygame.Rect(int(playerX - offsetW), int(playerY + playerH / 2 - offsetH / 2), offsetW, offsetH)
    else:
        if playerFaceY >= 0:
            return pygame.Rect(int(playerX + playerW / 2 - offsetW / 2), int(playerY + playerH), offsetW, offsetH)
        else:
            return pygame.Rect(int(playerX + playerW / 2 - offsetW / 2), int(playerY - offsetH), offsetW, offsetH)

def updateIntroScene(deltaTime):
    global stage, hasChest, shakeTimer, stageMessageTimer, interactRequest, chestVisible
    updatePlayer(deltaTime)
    if interactRequest:
        playerRect = getPlayerRect()
        if chestVisible and playerRect.colliderect(chestRect) and not hasChest:
            hasChest = True
            chestVisible = False
            startIntroChestCutscene()
        interactRequest = False
    if stage == "introShaking":
        if shakeTimer > 0:
            shakeTimer -= deltaTime
    if stageMessageTimer > 0:
        stageMessageTimer -= deltaTime
        if stageMessageTimer < 0:
            stageMessageTimer = 0
    if stage == "introShaking" and stageMessageTimer <= 0:
        startNextRoom()

def handlePlayerInput(event):
    global interactRequest, stage, playerHealth, currentRoomNumber, doorUnlocked, keyCollected, switchActivated, trapActive
    
    # Handle regular game input
    if event.type == pygame.QUIT:
        global running
        running = False
    elif event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            running = False
        elif event.key == pygame.K_SPACE and stage == "playing":
            startAttack()
        elif event.key == pygame.K_e:
            interactRequest = True
        elif event.key == pygame.K_r and stage in ("gameover", "victory"):
            resetGame()
        elif event.key == pygame.K_q and stage in ("gameover", "victory"):
            running = False

def drawIntroScene(offsetX, offsetY):
    drawBackground(offsetX, offsetY)
    if chestVisible and chestImage:
        screen.blit(chestImage, (chestRect.x + offsetX, chestRect.y + offsetY))
    drawPlayerSprite(offsetX, offsetY)
    if stageMessageTimer > 0:
        textSurface = fontSmall.render(stageMessage, True, (255, 255, 255))
        screen.blit(textSurface, (screenWidth // 2 - textSurface.get_width() // 2 + offsetX, 30 + offsetY))

def drawPlayerSprite(offsetX, offsetY):
    playerRect = getPlayerRect()
    drawX = playerRect.x + offsetX
    drawY = playerRect.y + offsetY
    frame = getPlayerAnimationFrame()
    if frame:
        frameToDraw = frame
        if playerFacingLeft:
            frameToDraw = pygame.transform.flip(frame, True, False)
        screen.blit(frameToDraw, (drawX, drawY))
    else:
        pygame.draw.rect(screen, (180, 200, 90), pygame.Rect(drawX, drawY, playerRect.width, playerRect.height))

def drawBackground(offsetX=0, offsetY=0):
    if backgroundImage:
        bg = pygame.transform.scale(backgroundImage, (screenWidth, screenHeight))
        screen.blit(bg, (offsetX, offsetY))
    else:
        screen.fill((20, 20, 40))

def fillRectWithTile(rect):
    if not tileImage:
        pygame.draw.rect(screen, (80, 80, 120), rect)
        return
    tileW = tileImage.get_width()
    tileH = tileImage.get_height()
    for y in range(rect.top, rect.bottom, tileH):
        for x in range(rect.left, rect.right, tileW):
            screen.blit(tileImage, (x, y))

def drawCurrentRoom(offsetX, offsetY):
    drawBackground(offsetX, offsetY)

    # Draw the actual game elements
    for wall in wallsList:
        fillRectWithTile(pygame.Rect(int(wall.x + offsetX), int(wall.y + offsetY), wall.width, wall.height))
    if keyRect:
        if keyImage:
            screen.blit(keyImage, (keyRect.x + offsetX, keyRect.y + offsetY))
        else:
            pygame.draw.rect(screen, (200, 180, 60), pygame.Rect(keyRect.x + offsetX, keyRect.y + offsetY, keyRect.width, keyRect.height))
    if switchRect:
        pygame.draw.rect(screen, (180, 100, 35), pygame.Rect(switchRect.x + offsetX, switchRect.y + offsetY, switchRect.width, switchRect.height))
    if trapActive:
        for trapRect in trapRects:
            pygame.draw.rect(screen, (200, 40, 40), pygame.Rect(trapRect.x + offsetX, trapRect.y + offsetY, trapRect.width, trapRect.height))
    else:
        for trapRect in trapRects:
            pygame.draw.rect(screen, (80, 80, 80), pygame.Rect(trapRect.x + offsetX, trapRect.y + offsetY, trapRect.width, trapRect.height))
    doorColor = (60, 180, 60) if doorUnlocked else (180, 60, 60)
    pygame.draw.rect(screen, doorColor, pygame.Rect(doorRect.x + offsetX, doorRect.y + offsetY, doorRect.width, doorRect.height))
    drawPlayerSprite(offsetX, offsetY)
    for enemy in enemiesList:
        enemyRect = pygame.Rect(int(enemy["x"] + offsetX), int(enemy["y"] + offsetY), enemy["w"], enemy["h"])
        
        # Update animation frame
        if enemy["mode"] == "chase":
            frames = flyBadGuyWalkFrames if enemy.get('is_moving', False) else flyBadGuyIdleFrames
            if frames:
                enemy['frame_timer'] += deltaTime
                if enemy['frame_timer'] >= enemy.get('frame_delay', 0.1):
                    enemy['frame_timer'] = 0
                    enemy['frame_index'] = (enemy['frame_index'] + 1) % len(frames)
                
                # Draw the current frame
                frame = frames[enemy['frame_index']]
                # Flip the frame if needed based on movement direction
                if enemy.get('last_dx', 0) < 0:  # Moving left
                    frame = pygame.transform.flip(frame, True, False)
                screen.blit(frame, (enemyRect.x, enemyRect.y))
            else:
                # Fallback to rectangle if no frames loaded
                pygame.draw.rect(screen, (220, 60, 60), enemyRect)
        else:
            # Original behavior for non-chasing enemies
            pygame.draw.rect(screen, (60, 140, 200), enemyRect)
    if attackActive:
        attackRect = getAttackRect()
        pygame.draw.rect(screen, (250, 250, 80), pygame.Rect(attackRect.x + offsetX, attackRect.y + offsetY, attackRect.width, attackRect.height))
    if stageMessageTimer > 0:
        textSurface = fontSmall.render(stageMessage, True, (255, 255, 255))
        screen.blit(textSurface, (screenWidth // 2 - textSurface.get_width() // 2 + offsetX, 20 + offsetY))

def drawHud():
    # Draw regular HUD
    healthText = f"Health: {playerHealth}"
    healthSurface = fontSmall.render(healthText, True, (255, 255, 255))
    screen.blit(healthSurface, (20, 20))
    roomText = f"Room {currentRoomNumber} / 10"
    roomSurface = fontSmall.render(roomText, True, (255, 255, 255))
    screen.blit(roomSurface, (20, 50))
    keyStatus = "Key: Yes" if keyCollected else "Key: No"
    keySurface = fontSmall.render(keyStatus, True, (255, 255, 255))
    screen.blit(keySurface, (20, 80))



def drawGameOver():
    screen.fill((10, 10, 10))
    frame = getPlayerAnimationFrame()
    if frame:
        bmpX = screenWidth // 2 - playerW // 2
        bmpY = screenHeight // 2 - playerH // 2 - 40
        screen.blit(frame, (bmpX, bmpY))
    overSurface = fontLarge.render("Game Over", True, (255, 60, 60))
    screen.blit(overSurface, (screenWidth // 2 - overSurface.get_width() // 2, screenHeight // 2 - 60))
    infoSurface = fontSmall.render("Press R to restart or Q to quit", True, (220, 220, 220))
    screen.blit(infoSurface, (screenWidth // 2 - infoSurface.get_width() // 2, screenHeight // 2 + 10))

def drawVictory():
    screen.fill((15, 40, 15))
    winSurface = fontLarge.render("You escaped the temple!", True, (200, 255, 200))
    screen.blit(winSurface, (screenWidth // 2 - winSurface.get_width() // 2, screenHeight // 2 - 60))
    infoSurface = fontSmall.render("Press R to restart or Q to quit", True, (220, 220, 220))
    screen.blit(infoSurface, (screenWidth // 2 - infoSurface.get_width() // 2, screenHeight // 2 + 10))

def resetGame():
    global interactRequest, attackActive, attackTimer, attackCooldownTimer, shakeTimer, playerMoving, walkFrameIndex, walkFrameTimer
    global playerIdleFrameIndex, playerIdleFrameTimer, playerHurtTimer, playerHurtFrameIndex, playerHurtFrameTimer, playerDeathFrameIndex, playerDeathFrameTimer
    interactRequest = False
    attackActive = False
    attackTimer = 0.0
    attackCooldownTimer = 0.0
    shakeTimer = 0.0
    playerMoving = False
    walkFrameIndex = 0
    walkFrameTimer = 0.0
    playerIdleFrameIndex = 0
    playerIdleFrameTimer = 0.0
    playerHurtTimer = 0.0
    playerHurtFrameIndex = 0
    playerHurtFrameTimer = 0.0
    playerDeathFrameIndex = 0
    playerDeathFrameTimer = 0.0
    setStageMessage("", 0.0)
    startIntroScene()

pygame.init()
screen = pygame.display.set_mode((screenWidth, screenHeight))
pygame.display.set_caption("Temple Escape")
clock = pygame.time.Clock()
fontLarge = pygame.font.SysFont(None, 48)
fontSmall = pygame.font.SysFont(None, 24)
# Load player animations
playerWalkingFrames = loadAnimationFrames("assets/walking/WalkingCaveExplorer-Sheet.png")
playerIdleFrames = loadAnimationFrames("assets/idle/IdleCaveExplorer-Sheet.png")

# Try to load hurt and death animations if available, but don't fail if they're missing
try:
    playerHurtFrames = loadAnimationFrames("assets/hurt/player_hurt.png")
except:
    playerHurtFrames = []
    print("Warning: Could not load hurt animation")

try:
    playerDeathFrames = loadAnimationFrames("assets/death/player_death.png")
except:
    playerDeathFrames = []
    print("Warning: Could not load death animation")

# Load enemy animations
try:
    # Load the actual enemy sprites
    flyBadGuyWalkFrames = loadAnimationFrames("assets/flyBadGuy/move/Bones_Skull_Run.png", 32, 32)
    flyBadGuyIdleFrames = loadAnimationFrames("assets/flyBadGuy/idle/Bones_Skull_Idle.png", 32, 32)
    
    if flyBadGuyWalkFrames and flyBadGuyIdleFrames:
        print("Successfully loaded enemy animations")
    else:
        print("Warning: Could not load enemy animations")
        
except Exception as e:
    print(f"Warning: Could not load enemy animations: {e}")
    flyBadGuyWalkFrames = []
    flyBadGuyIdleFrames = []

# Initialize enemy animation states
for enemy in enemiesList:
    enemy['frame_index'] = 0
    enemy['frame_timer'] = 0.0
    enemy['frame_delay'] = 0.1
    enemy['is_moving'] = False

try:
    backgroundImage = pygame.image.load("assets/map/bg/stoneBackground.png").convert()
except pygame.error:
    backgroundImage = None
try:
    tileImage = pygame.image.load("assets/map/tile/tile_54.png").convert_alpha()
except pygame.error:
    tileImage = None
try:
    keyImage = pygame.image.load("assets/items/keys/keys.png").convert_alpha()
    keyImage = pygame.transform.smoothscale(keyImage, (keyWidth, keyHeight))
except pygame.error:
    keyImage = None
try:
    chestImage = pygame.image.load("assets/items/chest/chest.png").convert_alpha()
    chestImage = pygame.transform.smoothscale(chestImage, (chestRect.width, chestRect.height))
except pygame.error:
    chestImage = None
resetGame()
while running:
    deltaTime = clock.tick(60) / 1000.0
    for event in pygame.event.get():
        handlePlayerInput(event)
    noiseCounter = 0
    if noiseCounter < 1:
        noiseCounter += 1
    if stage == "intro":
        updateIntroScene(deltaTime)
        offsetX = random.randint(-4, 4) if shakeTimer > 0 else 0
        offsetY = random.randint(-4, 4) if shakeTimer > 0 else 0
        drawIntroScene(offsetX, offsetY)
    elif stage == "introCutscene":
        updateIntroCutscene(deltaTime)
        drawIntroScene(0, 0)
    elif stage == "introShaking":
        updateIntroScene(deltaTime)
        offsetX = random.randint(-6, 6)
        offsetY = random.randint(-6, 6)
        drawIntroScene(offsetX, offsetY)
    elif stage == "playing":
        updatePlayer(deltaTime)
        updateEnemies(deltaTime)
        handleCollisions(deltaTime)
        if stage != "playing":
            continue
        if stageMessageTimer > 0:
            stageMessageTimer -= deltaTime
            if stageMessageTimer < 0:
                stageMessageTimer = 0
        offsetX = random.randint(-2, 2) if shakeTimer > 0 else 0
        offsetY = random.randint(-2, 2) if shakeTimer > 0 else 0
        if shakeTimer > 0:
            shakeTimer -= deltaTime
        drawCurrentRoom(offsetX, offsetY)
        drawHud()
        interactRequest = False
    elif stage == "exitCutscene":
        updateExitCutscene(deltaTime)
        drawCurrentRoom(0, 0)
        drawHud()
    elif stage == "gameover":
        animatePlayer(deltaTime)
        drawGameOver()
    elif stage == "victory":
        drawVictory()
    pygame.display.flip()
pygame.quit()
