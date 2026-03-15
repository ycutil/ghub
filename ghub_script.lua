-- Aion 2 Auto-Skill Activation (G-Hub Lua Script)
--
-- 설정 순서:
-- 1. G-Hub에서 아이온2 프로필 생성 (실행 파일 지정)
-- 2. 마우스 → Assignments → Scripting에 이 내용 붙여넣기
-- 3. SKILL_KEY를 게임 내 스킬 단축키와 일치시키기

SKILL_KEY = "f1"         -- 게임 내 상태이상 해제 스킬 키
POLL_INTERVAL = 30       -- ScrollLock 폴링 간격 (ms)
LUA_COOLDOWN = 300       -- 이중 발동 방지 쿨다운 (ms)

function OnEvent(event, arg)
    if event == "PROFILE_ACTIVATED" then
        local last_trigger = 0
        while true do
            if IsKeyLockOn("scrolllock") then
                local now = GetRunningTime()
                if (now - last_trigger) >= LUA_COOLDOWN then
                    PressAndReleaseKey(SKILL_KEY)
                    last_trigger = now
                end
            end
            Sleep(POLL_INTERVAL)
        end
    end
end
