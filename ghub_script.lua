SKILL_KEY = "f1"
POLL_INTERVAL = 2        -- 2ms 폴링
LUA_COOLDOWN = 300
PRESS_COUNT = 20         -- 키 반복 횟수
PRESS_INTERVAL = 1       -- 반복 간격 (ms)

function OnEvent(event, arg)
    if event == "PROFILE_ACTIVATED" then
        local last_trigger = 0

        while true do
            if IsKeyLockOn("scrolllock") then
                local now = GetRunningTime()
                if (now - last_trigger) >= LUA_COOLDOWN then
                    for i = 1, PRESS_COUNT do
                        PressAndReleaseKey(SKILL_KEY)
                        if i < PRESS_COUNT then
                            Sleep(PRESS_INTERVAL)
                        end
                    end
                    last_trigger = GetRunningTime()
                end
                PressAndReleaseKey("scrolllock")
            end
            Sleep(POLL_INTERVAL)
        end
    end
end
