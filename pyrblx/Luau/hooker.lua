local HttpService = game:GetService("HttpService")
local WebSocketService = game:GetService("WebSocketService")
local RobloxReplicatedStorage = game:GetService("RobloxReplicatedStorage")
local CorePackages = game:GetService("CorePackages")

local EXECUTOR_NAME, EXECUTOR_VERSION, PROCESS_ID = "%EXECUTOR_NAME%", "%EXECUTOR_VERSION%", "%PROCESS_ID%"

local executorContainer, scriptContainer = Instance.new("Folder"), Instance.new("Folder")
executorContainer.Name = EXECUTOR_NAME
executorContainer.Parent = RobloxReplicatedStorage

scriptContainer.Name = "Scripts"
scriptContainer.Parent = executorContainer

local Utils, Executor = {}, {}

function Utils:GetRandomModule()
    local children = CorePackages.Packages:GetChildren()
    local module

    while not module or module.ClassName ~= "ModuleScript" do
        module = children[math.random(#children)]
    end

    return module
end

Executor.Host = "localhost"
Executor.Port = "8080"

function Executor:OnConnect()
    self.client = WebSocketService:CreateClient("ws://" .. self.Host .. ":" .. self.Port)

    if self.client then
        print("Hook connected!")
    else
        print("Hook failed to connect!")
    end
end

function Executor:OnData(data)
    print("Hook receiving data!")

    local success, request = pcall(function()
        return HttpService:JSONDecode(data)
    end)

    if success then
        print("Data successfully interpreted!")

        if request.type == "request" then
            local message = ""

            if request.action == "getModule" then
                local module = Utils:GetRandomModule()

                local clone = module:Clone()
                clone.Name = HttpService:GenerateGUID(false)
                clone.Parent = scriptContainer

                message = clone.Name
            elseif request.action == "requireModule" then
                local module = scriptContainer:FindFirstChild(request.data)
                local func = require(module)
                module:Destroy()

                message = ""
            end

            local response = {
                type = "response",
                id = request.id,
                data = message
            }
            
            print("Hook sending response...")
            self.client:Send(HttpService:JSONEncode(response))
        end
    end
end

function Executor:OnDisconnect()
    print("Hook disconnected!")
end

function Executor:Init()
    self:OnConnect()

    if self.client then
        self.client.MessageReceived:Connect(function(message)
            self:OnData(message)
        end)
        self.client.Closed:Connect(function()
            self:OnDisconnect()
        end)
    end
end

print("Hook successfully injected!")

Executor:Init()