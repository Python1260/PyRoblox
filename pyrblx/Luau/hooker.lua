local HttpService = game:GetService("HttpService")
local WebSocketService = game:GetService("WebSocketService")
local RobloxReplicatedStorage = game:GetService("RobloxReplicatedStorage")
local CorePackages = game:GetService("CorePackages")
local EncodingService = game:GetService("EncodingService")

local EXECUTOR_NAME, EXECUTOR_VERSION, PROCESS_ID, WEBSOCKET_HOST, WEBSOCKET_PORT = "%EXECUTOR_NAME%", "%EXECUTOR_VERSION%", "%PROCESS_ID%", "%WEBSOCKET_HOST%", "%WEBSOCKET_PORT%"
local USER_AGENT = EXECUTOR_NAME .. "/" .. EXECUTOR_VERSION
local HWID = HttpService:GenerateGUID(false)

local executorContainer, scriptContainer, objectContainer = Instance.new("Folder"), Instance.new("Folder"), Instance.new("Folder")
executorContainer.Name = EXECUTOR_NAME
executorContainer.Parent = RobloxReplicatedStorage

scriptContainer.Name = "Scripts"
scriptContainer.Parent = executorContainer

objectContainer.Name = "Objects"
objectContainer.Parent = executorContainer

local Utils, WebSocket, Executor = {}, {}, {}
local LOADED = false
local LOADEVENT = Instance.new("BindableEvent")

function Utils:Trace(message, error)
    local text = "[" .. EXECUTOR_NAME .. "]" .. " " .. message

    if error then
        warn(text)
    else
        print(text)
    end
end

function Utils:GetRandomModule()
    local children = CorePackages.Packages:GetChildren()
    local module

    while not module or module.ClassName ~= "ModuleScript" do
        module = children[math.random(#children)]
    end

    return module
end

function Utils:CloneRandomModule()
    local module = self:GetRandomModule()

    local clone = module:Clone()
    clone.Name = HttpService:GenerateGUID(false)
    clone.Parent = scriptContainer

    return clone
end

function Utils:GetPointer(object)
    local inst = Instance.new("ObjectValue")
    inst.Name = HttpService:GenerateGUID(false)
    inst.Parent = objectContainer
    inst.Value = object

    return inst
end

function Utils:ForceEnvironment(func)
    local env = getfenv(func)

    for key, value in pairs(Executor) do
        env[key] = value
    end

    setfenv(func, env)
end

WebSocket.Requests = {}
WebSocket.SignalHandlers = {}

function WebSocket:Send(id, action, data)
    if self.connection then
        local response = {
            type = "client",
            id = id,
            action = action,
            data = data
        }

        Utils:Trace("WebSocket sending data...")
        self.connection:Send(HttpService:JSONEncode(response))
    end
end

function WebSocket:SendAndReceive(action, data, timeout)
    timeout = timeout or 5

    local id = HttpService:GenerateGUID(false)
    self:Send(id, action, data)

    local responseAction, responseData
    local event = Instance.new("BindableEvent")

    self.Requests[id] = function(ra, rd)
        responseAction = ra
        responseData = rd
        event:Fire()
    end

    task.spawn(function()
        local startTime = os.clock()

        while not responseAction do
            if (os.clock() - startTime) > timeout then
                event:Fire()
                break
            end
            task.wait()
        end
    end)

    event.Event:Wait()

    event:Destroy()
    self.Requests[id] = nil

    return responseAction, responseData
end

function WebSocket:OnConnect()
    self.connection = WebSocketService:CreateClient("ws://" .. self.Host .. ":" .. self.Port)

    if self.connection then
        Utils:Trace("WebSocket connected!")
    else
        Utils:Trace("WebSocket failed to connect!")
    end
end

function WebSocket:OnData(data)
    Utils:Trace("WebSocket receiving data!")

    local success, request = pcall(function()
        return HttpService:JSONDecode(data)
    end)

    if success then
        Utils:Trace("Data successfully interpreted!")

        local req_type = request.type
        local req_id = request.id
        local req_action = request.action
        local req_data = request.data

        if req_type == "server" then
            local func = self.Requests[req_id]
            if func then
                func(req_action, req_data)
                self.Requests[req_id] = nil
            end

            local handlers = self.SignalHandlers[req_action]
            if handlers then
               for _, handler in pairs(handlers) do
                    local message = handler(req_id, req_data)

                    if message then
                       self:Send(request.id, req_action, message) 
                    end
                end 
            end
        end
    end
end

function WebSocket:OnDisconnect()
    Utils:Trace("WebSocket disconnected!")
    self.connection = nil
end

function WebSocket:On(name, func)
    local handlers = self.SignalHandlers[name] or {}
    table.insert(handlers, func)
    self.SignalHandlers[name] = handlers
end

function WebSocket:Init(host, port)
    self.Host = host
    self.Port = port
    self:OnConnect()

    if self.connection then
        self.__onMessageReceived = self.connection.MessageReceived:Connect(function(message)
            self:OnData(message)
        end)
        self.__onClosed = self.connection.Closed:Connect(function()
            self:OnDisconnect()
            self.__onMessageReceived:Disconnect()
            self.__onClosed:Disconnect()
        end)
    else
        self.connection = nil
    end
end

Utils:Trace("Hook successfully injected!")

WebSocket:On("handshake", function(id, data)
    local loaded = LOADED or LOADEVENT.Event:Wait()

    return "success"
end)
WebSocket:On("getModule", function(id, data)
    local module = Utils:CloneRandomModule()

    return module.Name
end)
WebSocket:On("requireModule", function(id, data)
    local module = scriptContainer:FindFirstChild(data)

    if module then
        local func = require(module)

        Utils:ForceEnvironment(func)
        func()

        module:Destroy()

        return "success"
    end

    return "error"
end)

WebSocket:Init(WEBSOCKET_HOST, WEBSOCKET_PORT)

function Executor.loadstring(chunk, chunkname)
    local module = Utils:CloneRandomModule()
    local action, data = WebSocket:SendAndReceive("loadstring", { Source = chunk, Module = module.Name })

    if action == "success" then
        local func = require(module)

        Utils:ForceEnvironment(func)

        module:Destroy()

        return func
    end

    Utils:Trace("loadstring failed to compile source!", true)
    return function() return {} end
end

function Executor.request(options)
    options.Method = options.Method or "GET"
    options.Method = options.Method:upper()

    options.Headers = options.Headers or {}
    options.Headers["User-Agent"] = options.Headers["User-Agent"] or USER_AGENT
    options.Headers["Exploit-Guid"] = tostring(HWID)
    options.Headers["Roblox-Place-Id"] = tostring(game.PlaceId)
    options.Headers["Roblox-Game-Id"] = tostring(game.JobId)
    options.Headers["Roblox-Session-Id"] = HttpService:JSONEncode({
        GameId = tostring(game.JobId),
        PlaceId = tostring(game.PlaceId)
    })

    if options.Cookies then
        local cookie = ""

        for key, value in pairs(options.Cookies) do
            cookie = cookie .. name .. "=" .. tostring(value) .. "; "
        end

        cookie = cookie:sub(1, -3)
        options.Headers["Cookie"] = cookie
    end

    local action, data = WebSocket:SendAndReceive("httprequest", options)

    if action == "success" then
        return data
    end

    Utils:Trace("request failed to fetch data!", true)
    return "{}"
end
Executor.http = {
    request = Executor.request
}
Executor.http_request = Executor.request

function Executor.HttpGet(url, raw)
    local action, data = WebSocket:SendAndReceive("httpget", { Url = url })

    if action == "success" then
        return data
    end

    Utils:Trace("HttpGet failed to get page contents!", true)
    return ""
end

function Executor.HttpPost(url, data, content_type)
    content_type = content_type or "application/json"

    return Executor.request({
        Url = url,
        Method = "POST",
        Body = data,
        Headers = {
            ["Content-Type"] = content_type
        }
    })
end

Executor.base64 = {}

function Executor.base64.encode(data)
    return buffer.tostring(EncodingService:Base64Encode(buffer.fromstring(data)))
end

function Executor.base64.decode(data)
    return buffer.tostring(EncodingService:Base64Decode(buffer.fromstring(data)))
end

Executor.base64_encode = Executor.base64.encode
Executor.base64_decode = Executor.base64.decode
Executor.base64encode = Executor.base64.encode
Executor.base64decode = Executor.base64.decode

Executor.crypt = {
    base64 = Executor.base64,
    base64_encode = Executor.base64.encode,
    base64_decode = Executor.base64.decode,
    base64encode = Executor.base64.encode,
    base64decode = Executor.base64.decode,
}

function Executor.crypt.generatekey(length)
end

function Executor.crypt.encrypt(data, key, iv, algorithm)
end

function Executor.crypt.decrypt(cipher, key, iv, algorithm)
end

local lz4_lib = (function()
    local request = Executor.HttpGet("https://raw.githubusercontent.com/Mitutoyum/lz4-lua/refs/heads/main/lz4.lua")

    if request then
        local lib = Executor.loadstring(request)()

        if lib then
           return lib 
        end
    end

    Utils:Trace("failed to load lz4 library!", true)
    return nil
end)()

if lz4_lib then
    Executor.lz4 = lz4_lib
    Executor.lz4compress = Executor.lz4.compress
    Executor.lz4decompress = Executor.lz4.decompress    
end


local drawing_lib = (function()
    local request = Executor.HttpGet("https://raw.githubusercontent.com/Mitutoyum/drawing-library/refs/heads/main/drawing.lua")

    if request then
        local lib = Executor.loadstring(request)()

        if lib then
           return lib
        end
    end

    Utils:Trace("failed to load drawing library!")
    return nil
end)()

if drawing_lib then
    Executor.Drawing = drawing_lib.Drawing
    for name, func in drawing_lib.functions do
        Executor[name] = func
    end
end

function Executor.getgenv()
    return Executor
end

function Executor.gethwid()
    return HWID
end

function Executor.getexecutorname()
    return EXECUTOR_NAME
end

function Executor.getexecutorversion()
    return EXECUTOR_VERSION
end

function Executor.identifyexecutor()
    return EXECUTOR_NAME, EXECUTOR_VERSION
end

function Executor.getinstances()
    return game:GetDescendants()
end

function Executor.getscriptbytecode(target)
    local pointer = Utils:GetPointer(target)

    local action, data = WebSocket:SendAndReceive("getscriptbytecode", { Pointer = pointer.Name })

    pointer:Destroy()

    if action == "success" then
        return data
    end

    Utils:Trace("getscriptbytecode failed to get script bytecode!")
end

function Executor.getscripthash(target)
    return target:GetHash()
end

function Executor.queue_on_teleport(chunk)
    local action, data = WebSocket:SendAndReceive("queueonteleport", { Source = chunk })

    if action == "success" then
        return true
    end

    Utils:Trace("queue_on_teleport failed to queue source!")
end

Executor.queueonteleport = Executor.queue_on_teleport

Executor.game = {}
setmetatable(Executor.game, {
    __index = function(self, index)
        if index == "HttpGet" or index == "HttpGetAsync" then
            return function(_, ...)
                return Executor.HttpGet(...)
            end
        elseif index == "HttpPost" or index == "HttpPostAsync" then
            return function(_, ...)
                return Executor.HttpPost(...)
            end
        end

        if type(game[index]) == "function" then
            return function(_, ...)
                return game[index](game, ...)
            end
        end

        return game[index]
    end,

    __tostring = function(self)
        return game.Name
    end,

    __metatable = getmetatable(game)
})

LOADED = true
LOADEVENT:Fire()
Utils:Trace("Executor loaded!")