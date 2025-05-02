import React from 'react';
import { 
  Typography, 
  Paper, 
  Box, 
  Divider, 
  Chip,
  Link,
  CircularProgress
} from '@mui/material';

const NodeDetails = ({ node, details }) => {
  if (!node) return null;
  
  const { data } = node;
  
  return (
    <Paper elevation={0} className="node-details">
      <Typography variant="h5" gutterBottom>
        {node.id}
      </Typography>
      
      {data.metadata?.docstring && (
        <Box mb={2}>
          <Typography variant="subtitle2" color="text.secondary">
            Documentation
          </Typography>
          <Typography variant="body2">
            {data.metadata.docstring}
          </Typography>
        </Box>
      )}
      
      {data.metadata?.location && (
        <Box mb={2}>
          <Typography variant="subtitle2" color="text.secondary">
            Source Location
          </Typography>
          <Link href="#" underline="hover">
            <Typography variant="body2">
              {data.metadata.location.file_path}:{data.metadata.location.line_no}
            </Typography>
          </Link>
        </Box>
      )}
      
      <Divider sx={{ my: 2 }} />
      
      <Box mb={2}>
        <Typography variant="subtitle2" color="text.secondary">
          Dependencies
        </Typography>
        {data.dependencies.length > 0 ? (
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
            {data.dependencies.map(dep => (
              <Chip 
                key={dep} 
                label={dep} 
                size="small" 
                color="primary" 
                variant="outlined" 
              />
            ))}
          </Box>
        ) : (
          <Typography variant="body2">No dependencies</Typography>
        )}
      </Box>
      
      <Box mb={2}>
        <Typography variant="subtitle2" color="text.secondary">
          Used By
        </Typography>
        {data.used_by.length > 0 ? (
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
            {data.used_by.map(dep => (
              <Chip 
                key={dep} 
                label={dep} 
                size="small" 
                color="secondary" 
                variant="outlined" 
              />
            ))}
          </Box>
        ) : (
          <Typography variant="body2">Not used by any other components</Typography>
        )}
      </Box>
      
      {data.spec && (
        <Box mb={2}>
          <Typography variant="subtitle2" color="text.secondary">
            Specification
          </Typography>
          <Paper 
            variant="outlined" 
            sx={{ 
              p: 1, 
              backgroundColor: '#f5f5f5', 
              fontFamily: 'monospace',
              fontSize: '0.85rem',
              overflow: 'auto'
            }}
          >
            <pre style={{ margin: 0 }}>{data.spec}</pre>
          </Paper>
        </Box>
      )}
      
      {details && details.source_code && (
        <Box mb={2}>
          <Typography variant="subtitle2" color="text.secondary">
            Source Code
          </Typography>
          <Paper 
            variant="outlined" 
            sx={{ 
              p: 1, 
              backgroundColor: '#f5f5f5', 
              fontFamily: 'monospace',
              fontSize: '0.85rem',
              overflow: 'auto'
            }}
          >
            <pre style={{ margin: 0 }}>{details.source_code}</pre>
          </Paper>
        </Box>
      )}
      
      {!details && node.id && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
          <CircularProgress size={24} />
        </Box>
      )}
    </Paper>
  );
};

export default NodeDetails;
