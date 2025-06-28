'use client'

import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Play,
  Pause,
  SkipForward,
  SkipBack,
  RotateCcw,
  Settings,
  Clock,
  Users,
  Shield,
  Zap,
  ChevronDown,
  ChevronUp
} from 'lucide-react'

interface DemoStep {
  step: number
  title: string
  description: string
  user_input?: string
  expected_agent?: string
  expected_handoff?: string
  expected_tool?: string
  demo_notes: string
}

interface DemoScenario {
  id: string
  name: string
  description: string
  duration_minutes: number
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  tags: string[]
  steps: DemoStep[]
  success_criteria: string[]
}

interface DemoControlPanelProps {
  scenarios: Record<string, DemoScenario>
  onScenarioChange: (scenarioId: string) => void
  onStepChange: (step: number) => void
  onPlayPause: () => void
  onReset: () => void
  onSpeedChange: (speed: number) => void
  currentScenario: string
  currentStep: number
  isPlaying: boolean
  playbackSpeed: number
}

const DemoControlPanel: React.FC<DemoControlPanelProps> = ({
  scenarios,
  onScenarioChange,
  onStepChange,
  onPlayPause,
  onReset,
  onSpeedChange,
  currentScenario,
  currentStep,
  isPlaying,
  playbackSpeed
}) => {
  const [isExpanded, setIsExpanded] = useState(true)
  const [showSettings, setShowSettings] = useState(false)

  const scenario = scenarios[currentScenario]
  const totalSteps = scenario?.steps.length || 0
  const progress = totalSteps > 0 ? (currentStep / totalSteps) * 100 : 0

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty) {
      case 'beginner': return 'bg-green-100 text-green-800'
      case 'intermediate': return 'bg-yellow-100 text-yellow-800'
      case 'advanced': return 'bg-red-100 text-red-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getTagIcon = (tag: string) => {
    switch (tag) {
      case 'agents': case 'routing': case 'customer-service': return <Users className="w-3 h-3" />
      case 'security': case 'guardrails': case 'compliance': return <Shield className="w-3 h-3" />
      case 'enterprise': case 'mcp': case 'api-integration': return <Zap className="w-3 h-3" />
      case 'developer': case 'cli': case 'workflow': return <Settings className="w-3 h-3" />
      default: return null
    }
  }

  const speedOptions = [0.5, 1.0, 1.5, 2.0]

  return (
    <Card className="fixed top-4 right-4 w-96 z-50 shadow-lg border-2">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
            <CardTitle className="text-lg">Demo Control</CardTitle>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </Button>
        </div>
        {isExpanded && (
          <CardDescription>
            Interactive demo scenarios for OpenAI Agents Enterprise
          </CardDescription>
        )}
      </CardHeader>

      {isExpanded && (
        <CardContent className="space-y-4">
          {/* Scenario Selection */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Current Scenario</label>
            <select
              value={currentScenario}
              onChange={(e) => onScenarioChange(e.target.value)}
              className="w-full p-2 border rounded-md text-sm"
            >
              {Object.entries(scenarios).map(([id, scenario]) => (
                <option key={id} value={id}>
                  {scenario.name}
                </option>
              ))}
            </select>
          </div>

          {/* Scenario Info */}
          {scenario && (
            <div className="space-y-2">
              <div className="flex items-center gap-2 flex-wrap">
                <Badge className={getDifficultyColor(scenario.difficulty)}>
                  {scenario.difficulty}
                </Badge>
                <Badge variant="outline" className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {scenario.duration_minutes}m
                </Badge>
              </div>

              <div className="flex flex-wrap gap-1">
                {scenario.tags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="flex items-center gap-1 text-xs">
                    {getTagIcon(tag)}
                    {tag}
                  </Badge>
                ))}
              </div>

              <p className="text-sm text-gray-600">{scenario.description}</p>
            </div>
          )}

          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Progress</span>
              <span>{currentStep}/{totalSteps}</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
          </div>

          {/* Current Step Info */}
          {scenario && scenario.steps[currentStep - 1] && (
            <div className="p-3 bg-blue-50 rounded-md border">
              <h4 className="font-medium text-sm text-blue-900">
                Step {currentStep}: {scenario.steps[currentStep - 1].title}
              </h4>
              <p className="text-xs text-blue-700 mt-1">
                {scenario.steps[currentStep - 1].description}
              </p>
              {scenario.steps[currentStep - 1].user_input && (
                <div className="mt-2 p-2 bg-white rounded border text-xs">
                  <strong>Input:</strong> "{scenario.steps[currentStep - 1].user_input}"
                </div>
              )}
            </div>
          )}

          {/* Playback Controls */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onStepChange(Math.max(1, currentStep - 1))}
                disabled={currentStep <= 1}
              >
                <SkipBack className="w-4 h-4" />
              </Button>

              <Button
                variant={isPlaying ? "secondary" : "default"}
                size="sm"
                onClick={onPlayPause}
              >
                {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={() => onStepChange(Math.min(totalSteps, currentStep + 1))}
                disabled={currentStep >= totalSteps}
              >
                <SkipForward className="w-4 h-4" />
              </Button>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowSettings(!showSettings)}
              >
                <Settings className="w-4 h-4" />
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={onReset}
              >
                <RotateCcw className="w-4 h-4" />
              </Button>
            </div>
          </div>

          {/* Settings Panel */}
          {showSettings && (
            <div className="p-3 bg-gray-50 rounded-md border space-y-3">
              <h4 className="font-medium text-sm">Demo Settings</h4>

              <div className="space-y-2">
                <label className="text-xs font-medium">Playback Speed</label>
                <div className="flex gap-1">
                  {speedOptions.map((speed) => (
                    <Button
                      key={speed}
                      variant={playbackSpeed === speed ? "default" : "outline"}
                      size="sm"
                      className="text-xs px-2 py-1"
                      onClick={() => onSpeedChange(speed)}
                    >
                      {speed}x
                    </Button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-medium">Options</label>
                <div className="space-y-1">
                  <label className="flex items-center gap-2 text-xs">
                    <input type="checkbox" defaultChecked className="rounded" />
                    Show agent thinking
                  </label>
                  <label className="flex items-center gap-2 text-xs">
                    <input type="checkbox" defaultChecked className="rounded" />
                    Highlight UI elements
                  </label>
                  <label className="flex items-center gap-2 text-xs">
                    <input type="checkbox" defaultChecked className="rounded" />
                    Auto-advance steps
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* Success Criteria */}
          {scenario && (
            <div className="space-y-2">
              <h4 className="font-medium text-sm">Success Criteria</h4>
              <div className="space-y-1">
                {scenario.success_criteria.map((criteria, index) => (
                  <div key={index} className="flex items-center gap-2 text-xs">
                    <div className="w-2 h-2 bg-gray-300 rounded-full"></div>
                    <span className="text-gray-600">{criteria}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Demo Status */}
          <div className="pt-2 border-t">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>Demo Status</span>
              <span className="flex items-center gap-1">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                Ready
              </span>
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  )
}

export default DemoControlPanel

// Example usage component
export const DemoControlPanelExample: React.FC = () => {
  const [currentScenario, setCurrentScenario] = useState('customer_service_flow')
  const [currentStep, setCurrentStep] = useState(1)
  const [isPlaying, setIsPlaying] = useState(false)
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0)

  // Mock scenarios data - in real implementation, this would come from demo-flows.json
  const scenarios: Record<string, DemoScenario> = {
    customer_service_flow: {
      id: 'customer_service_flow',
      name: 'Customer Service Agent Flow',
      description: 'Demonstrates multi-agent customer service with intelligent routing',
      duration_minutes: 4,
      difficulty: 'beginner',
      tags: ['agents', 'routing', 'customer-service'],
      steps: [
        {
          step: 1,
          title: 'Seat Change Request',
          description: 'User requests a seat change, demonstrating agent routing',
          user_input: 'Can I change my seat?',
          expected_agent: 'triage',
          expected_handoff: 'seat_booking',
          demo_notes: 'Shows intelligent routing from triage to specialist agent'
        },
        {
          step: 2,
          title: 'Confirmation Number Verification',
          description: 'Agent asks for confirmation number to proceed',
          user_input: 'My confirmation number is ABC123',
          expected_agent: 'seat_booking',
          demo_notes: 'Demonstrates context preservation and data lookup'
        }
      ],
      success_criteria: [
        'All agent handoffs occur correctly',
        'Context is preserved across handoffs',
        'Tools execute successfully'
      ]
    }
  }

  const handleScenarioChange = (scenarioId: string) => {
    setCurrentScenario(scenarioId)
    setCurrentStep(1)
    setIsPlaying(false)
  }

  const handleStepChange = (step: number) => {
    setCurrentStep(step)
  }

  const handlePlayPause = () => {
    setIsPlaying(!isPlaying)
  }

  const handleReset = () => {
    setCurrentStep(1)
    setIsPlaying(false)
  }

  const handleSpeedChange = (speed: number) => {
    setPlaybackSpeed(speed)
  }

  return (
    <DemoControlPanel
      scenarios={scenarios}
      onScenarioChange={handleScenarioChange}
      onStepChange={handleStepChange}
      onPlayPause={handlePlayPause}
      onReset={handleReset}
      onSpeedChange={handleSpeedChange}
      currentScenario={currentScenario}
      currentStep={currentStep}
      isPlaying={isPlaying}
      playbackSpeed={playbackSpeed}
    />
  )
}
