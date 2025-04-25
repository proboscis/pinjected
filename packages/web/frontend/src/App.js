import React, { useState, useCallback, useEffect } from 'react';
import ReactFlow, { 
  Background, 
  Controls, 
  MiniMap,
  useNodesState,
  useEdgesState
} from 'reactflow';
import 'reactflow/dist/style.css';
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  TextField, 
  Button, 
  Box, 
  Drawer, 
  CircularProgress,
  Select,
  MenuItem,
  FormControl,
  InputLabel
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import NodeDetails from './components/NodeDetails';
import axios from 'axios';

const DEFAULT_MODULE_PATH = 'pinjected_web.test_example.example_design';

function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNode, setSelectedNode] = useState(null);
  const [modulePath, setModulePath] = useState(DEFAULT_MODULE_PATH);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [nodeDetails, setNodeDetails] = useState(null);
  
  const fetchGraphData = async (path) => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get(`http://localhost:8000/api/graph/${path}`);
      setNodes(response.data.nodes);
      setEdges(response.data.edges);
    } catch (err) {
      console.error('Error fetching graph data:', err);
      setError(`Failed to load graph: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  const fetchNodeDetails = async (path, nodeKey) => {
    try {
      const response = await axios.get(`http://localhost:8000/api/node/${path}/${nodeKey}`);
      setNodeDetails(response.data);
    } catch (err) {
      console.error('Error fetching node details:', err);
    }
  };
  
  const handleSearch = async () => {
    if (!searchQuery) {
      fetchGraphData(modulePath);
      return;
    }
    
    try {
      const response = await axios.get(`http://localhost:8000/api/search/${modulePath}?query=${searchQuery}`);
      const searchResults = response.data.results;
      
      const updatedNodes = nodes.map(node => ({
        ...node,
        style: {
          ...node.style,
          opacity: searchResults.includes(node.id) ? 1 : 0.2,
        },
      }));
      
      setNodes(updatedNodes);
    } catch (err) {
      console.error('Error searching dependencies:', err);
      setError(`Search failed: ${err.message}`);
    }
  };
  
  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node);
    fetchNodeDetails(modulePath, node.id);
  }, [modulePath]);
  
  useEffect(() => {
    fetchGraphData(modulePath);
  }, [modulePath]);
  
  return (
    <div className="app-container">
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Pinjected DI Visualization
          </Typography>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <FormControl variant="outlined" size="small" sx={{ minWidth: 250, mr: 1, backgroundColor: 'white', borderRadius: 1 }}>
              <InputLabel id="module-path-label">Module Path</InputLabel>
              <Select
                labelId="module-path-label"
                value={modulePath}
                onChange={(e) => setModulePath(e.target.value)}
                label="Module Path"
              >
                <MenuItem value="pinjected_web.test_example.example_design">test_example.example_design</MenuItem>
                <MenuItem value="pinjected_reviewer.__pinjected__.__pinjected_reviewer_default_design">pinjected_reviewer.default_design</MenuItem>
              </Select>
            </FormControl>
            <TextField
              size="small"
              placeholder="Search dependencies..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              sx={{ mr: 1, backgroundColor: 'white', borderRadius: 1 }}
            />
            <Button 
              variant="contained" 
              color="secondary" 
              onClick={handleSearch}
              startIcon={<SearchIcon />}
            >
              Search
            </Button>
          </Box>
        </Toolbar>
      </AppBar>
      
      <div className="content">
        <div className="graph-container">
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
              <CircularProgress />
            </Box>
          ) : error ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
              <Typography color="error">{error}</Typography>
            </Box>
          ) : (
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              fitView
            >
              <Background />
              <Controls />
              <MiniMap />
            </ReactFlow>
          )}
        </div>
        
        <Drawer
          variant="permanent"
          anchor="right"
          sx={{
            width: 350,
            flexShrink: 0,
            '& .MuiDrawer-paper': {
              width: 350,
              boxSizing: 'border-box',
            },
          }}
        >
          <Toolbar />
          <Box sx={{ overflow: 'auto', p: 2 }}>
            {selectedNode ? (
              <NodeDetails node={selectedNode} details={nodeDetails} />
            ) : (
              <Typography variant="body1" color="text.secondary">
                Select a node to view details
              </Typography>
            )}
          </Box>
        </Drawer>
      </div>
    </div>
  );
}

export default App;
