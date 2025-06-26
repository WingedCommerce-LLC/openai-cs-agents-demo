"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import {
  Play,
  Square,
  Trash2,
  Plus,
  RefreshCw,
  Activity,
  Server,
  Settings,
  FileText,
  AlertCircle,
  CheckCircle,
  Clock,
  Zap
} from 'lucide-react';

interface MCPServer {
  id: string;
  name: string;
  description: string;
  status: string;
  endpoint_count: number;
  tool_count: number;
  complexity_score: number;
  created_at: string;
  updated_at: string;
}

interface MCPRegistryStats {
  total_servers: number;
  status_distribution: Record<string, number>;
  running_servers: number;
  total_endpoints: number;
  total_tools: number;
  average_complexity: number;
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'running':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'stopped':
      return <Square className="h-4 w-4 text-gray-500" />;
    case 'error':
      return <AlertCircle className="h-4 w-4 text-red-500" />;
    case 'generating':
      return <Clock className="h-4 w-4 text-blue-500" />;
    case 'generated':
      return <CheckCircle className="h-4 w-4 text-blue-500" />;
    default:
      return <Clock className="h-4 w-4 text-gray-400" />;
  }
};

const getStatusColor = (status: string) => {
  switch (status) {
    case 'running':
      return 'bg-green-100 text-green-800';
    case 'stopped':
      return 'bg-gray-100 text-gray-800';
    case 'error':
      return 'bg-red-100 text-red-800';
    case 'generating':
      return 'bg-blue-100 text-blue-800';
    case 'generated':
      return 'bg-blue-100 text-blue-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
};

export function MCPServerManager() {
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [stats, setStats] = useState<MCPRegistryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchServers = async () => {
    try {
      const response = await fetch('http://localhost:8000/mcp/servers');
      if (response.ok) {
        const data = await response.json();
        setServers(data.servers);
      }
    } catch (error) {
      console.error('Failed to fetch MCP servers:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch('http://localhost:8000/mcp/stats');
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch MCP stats:', error);
    }
  };

  const refreshData = async () => {
    setLoading(true);
    await Promise.all([fetchServers(), fetchStats()]);
    setLoading(false);
  };

  useEffect(() => {
    refreshData();
    // Refresh every 30 seconds
    const interval = setInterval(refreshData, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleServerAction = async (serverId: string, action: 'start' | 'stop' | 'delete') => {
    setActionLoading(serverId);
    try {
      const endpoint = action === 'delete'
        ? `http://localhost:8000/mcp/servers/${serverId}`
        : `http://localhost:8000/mcp/servers/${serverId}/${action}`;

      const method = action === 'delete' ? 'DELETE' : 'POST';

      const response = await fetch(endpoint, { method });

      if (response.ok) {
        await refreshData();
      } else {
        console.error(`Failed to ${action} server:`, await response.text());
      }
    } catch (error) {
      console.error(`Failed to ${action} server:`, error);
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Server className="h-5 w-5" />
            MCP Server Manager
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="h-6 w-6 animate-spin" />
            <span className="ml-2">Loading MCP servers...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Stats Overview */}
      {stats && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              MCP Registry Overview
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{stats.total_servers}</div>
                <div className="text-sm text-gray-600">Total Servers</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{stats.running_servers}</div>
                <div className="text-sm text-gray-600">Running</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">{stats.total_endpoints}</div>
                <div className="text-sm text-gray-600">Endpoints</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-orange-600">{stats.total_tools}</div>
                <div className="text-sm text-gray-600">Tools</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-indigo-600">{stats.average_complexity.toFixed(1)}</div>
                <div className="text-sm text-gray-600">Avg Complexity</div>
              </div>
              <div className="text-center">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={refreshData}
                  disabled={loading}
                >
                  <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Server List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              MCP Servers ({servers.length})
            </div>
            <Button variant="outline" size="sm">
              <Plus className="h-4 w-4 mr-2" />
              Add Server
            </Button>
          </CardTitle>
          <CardDescription>
            Manage your MCP servers and their lifecycle
          </CardDescription>
        </CardHeader>
        <CardContent>
          {servers.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Server className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No MCP servers registered</p>
              <p className="text-sm">Create your first server from an OpenAPI specification</p>
            </div>
          ) : (
            <ScrollArea className="h-96">
              <div className="space-y-4">
                {servers.map((server) => (
                  <div
                    key={server.id}
                    className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          {getStatusIcon(server.status)}
                          <h3 className="font-semibold">{server.name}</h3>
                          <Badge className={getStatusColor(server.status)}>
                            {server.status}
                          </Badge>
                        </div>

                        {server.description && (
                          <p className="text-sm text-gray-600 mb-2">{server.description}</p>
                        )}

                        <div className="flex items-center gap-4 text-sm text-gray-500">
                          <span className="flex items-center gap-1">
                            <FileText className="h-3 w-3" />
                            {server.endpoint_count} endpoints
                          </span>
                          <span className="flex items-center gap-1">
                            <Zap className="h-3 w-3" />
                            {server.tool_count} tools
                          </span>
                          <span className="flex items-center gap-1">
                            <Settings className="h-3 w-3" />
                            Complexity: {server.complexity_score.toFixed(1)}
                          </span>
                        </div>

                        <div className="text-xs text-gray-400 mt-2">
                          Created: {new Date(server.created_at).toLocaleDateString()}
                          {server.updated_at !== server.created_at && (
                            <span className="ml-2">
                              Updated: {new Date(server.updated_at).toLocaleDateString()}
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 ml-4">
                        {server.status === 'generated' || server.status === 'stopped' ? (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleServerAction(server.id, 'start')}
                            disabled={actionLoading === server.id}
                          >
                            {actionLoading === server.id ? (
                              <RefreshCw className="h-4 w-4 animate-spin" />
                            ) : (
                              <Play className="h-4 w-4" />
                            )}
                          </Button>
                        ) : server.status === 'running' ? (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleServerAction(server.id, 'stop')}
                            disabled={actionLoading === server.id}
                          >
                            {actionLoading === server.id ? (
                              <RefreshCw className="h-4 w-4 animate-spin" />
                            ) : (
                              <Square className="h-4 w-4" />
                            )}
                          </Button>
                        ) : null}

                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleServerAction(server.id, 'delete')}
                          disabled={actionLoading === server.id}
                          className="text-red-600 hover:text-red-700"
                        >
                          {actionLoading === server.id ? (
                            <RefreshCw className="h-4 w-4 animate-spin" />
                          ) : (
                            <Trash2 className="h-4 w-4" />
                          )}
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
