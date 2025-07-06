"""Tests for nx_graph_util.py module."""

from unittest.mock import patch, Mock, MagicMock

import networkx as nx
import pytest

from pinjected.nx_graph_util import NxGraphUtil


class TestNxGraphUtil:
    @pytest.fixture
    def simple_graph(self):
        """Create a simple directed graph for testing."""
        G = nx.DiGraph()
        G.add_edge("A", "B")
        G.add_edge("B", "C")
        G.add_edge("A", "C")
        return G

    @pytest.fixture
    def nx_util(self, simple_graph):
        """Create NxGraphUtil instance with simple graph."""
        return NxGraphUtil(graph=simple_graph)

    def test_init(self, simple_graph):
        """Test NxGraphUtil initialization."""
        util = NxGraphUtil(graph=simple_graph)
        assert util.graph is simple_graph
        assert isinstance(util.graph, nx.DiGraph)

    @patch("pinjected.nx_graph_util.Network")
    def test_to_physics_network(self, mock_network_class, nx_util):
        """Test converting graph to physics network."""
        mock_network = Mock()
        mock_network_class.return_value = mock_network

        result = nx_util.to_physics_network()

        # Verify Network was created with correct parameters
        mock_network_class.assert_called_once_with("1080px", "100%", directed=True)
        mock_network.from_nx.assert_called_once_with(nx_util.graph)
        mock_network.toggle_physics.assert_called_once_with(True)
        assert result is mock_network

    @patch("matplotlib.pyplot.show")
    @patch("matplotlib.pyplot.figure")
    @patch("pinjected.nx_graph_util.graphviz_layout")
    @patch("networkx.draw")
    def test_plot_mpl(self, mock_draw, mock_layout, mock_figure, mock_show, nx_util):
        """Test matplotlib plotting."""
        mock_pos = {"A": (0, 0), "B": (1, 1), "C": (2, 0)}
        mock_layout.return_value = mock_pos

        nx_util.plot_mpl()

        mock_figure.assert_called_once_with(figsize=(20, 20))
        mock_layout.assert_called_once_with(nx_util.graph, prog="dot")
        mock_draw.assert_called_once_with(nx_util.graph, with_labels=True, pos=mock_pos)
        mock_show.assert_called_once()

    @patch("os.system")
    @patch("platform.system")
    @patch("pinjected.nx_graph_util.Network")
    def test_save_as_html_on_darwin(
        self, mock_network_class, mock_platform, mock_system, nx_util
    ):
        """Test saving as HTML on macOS with show=True."""
        mock_platform.return_value = "Darwin"
        mock_network = Mock()
        mock_network_class.return_value = mock_network

        nx_util.save_as_html("test.html", show=True)

        mock_network.show.assert_called_once_with("test.html")
        mock_system.assert_called_once_with("open test.html")

    @patch("os.system")
    @patch("platform.system")
    @patch("pinjected.nx_graph_util.Network")
    def test_save_as_html_on_darwin_no_show(
        self, mock_network_class, mock_platform, mock_system, nx_util
    ):
        """Test saving as HTML on macOS with show=False."""
        mock_platform.return_value = "Darwin"
        mock_network = Mock()
        mock_network_class.return_value = mock_network

        nx_util.save_as_html("test.html", show=False)

        mock_network.show.assert_called_once_with("test.html")
        mock_system.assert_not_called()

    @patch("platform.system")
    @patch("pinjected.nx_graph_util.Network")
    def test_save_as_html_non_darwin(self, mock_network_class, mock_platform, nx_util):
        """Test saving as HTML on non-macOS system."""
        mock_platform.return_value = "Linux"
        mock_network = Mock()
        mock_network_class.return_value = mock_network

        nx_util.save_as_html("test.html", show=True)

        mock_network.show.assert_called_once_with("test.html")

    def test_save_as_html_invalid_name(self, nx_util):
        """Test save_as_html with invalid name type."""
        with pytest.raises(AssertionError):
            nx_util.save_as_html(123)  # Not a string

    @patch("os.chdir")
    @patch("os.getcwd")
    @patch("pinjected.nx_graph_util.Network")
    def test_save_as_html_at(
        self, mock_network_class, mock_getcwd, mock_chdir, nx_util, tmp_path
    ):
        """Test saving HTML at specific directory."""
        mock_getcwd.return_value = "/original/dir"
        mock_network = Mock()
        mock_network_class.return_value = mock_network

        dst_dir = tmp_path / "output"
        result = nx_util.save_as_html_at(dst_dir)

        # Verify directory operations
        assert dst_dir.exists()
        assert mock_chdir.call_count == 2
        mock_chdir.assert_any_call(dst_dir)
        mock_chdir.assert_any_call("/original/dir")

        # Verify network operations
        mock_network.write_html.assert_called_once_with(
            "graph.html", local=True, notebook=False
        )

        # Verify return value
        assert result == dst_dir / "graph.html"

    def test_save_as_html_at_invalid_path(self, nx_util):
        """Test save_as_html_at with invalid path type."""
        with pytest.raises(AssertionError):
            nx_util.save_as_html_at("/some/string/path")  # Not a Path object

    @patch("os.system")
    @patch("platform.system")
    @patch("pinjected.pinjected_logging.logger")
    @patch("pinjected.nx_graph_util.Network")
    def test_show_html_on_darwin(
        self, mock_network_class, mock_logger, mock_platform, mock_system, nx_util
    ):
        """Test show_html on macOS."""
        mock_platform.return_value = "Darwin"
        mock_network = Mock()
        mock_network_class.return_value = mock_network

        nx_util.show_html()

        mock_logger.info.assert_called_once_with("showing visualization html")
        mock_network.show.assert_called_once_with("di_visualiztion.html")
        # save_as_html is called which calls os.system twice
        assert mock_system.call_count == 2
        mock_system.assert_any_call("open di_visualiztion.html")

    @patch("platform.system")
    @patch("pinjected.pinjected_logging.logger")
    def test_show_html_non_darwin(self, mock_logger, mock_platform, nx_util):
        """Test show_html on non-macOS system."""
        mock_platform.return_value = "Linux"

        nx_util.show_html()

        mock_logger.warning.assert_called_once_with(
            "visualization of a design is disabled for non mac os."
        )

    @patch("time.sleep")
    @patch("os.system")
    @patch("os.chdir")
    @patch("os.getcwd")
    @patch("tempfile.TemporaryDirectory")
    @patch("pinjected.nx_graph_util.Network")
    def test_show_html_temp(
        self,
        mock_network_class,
        mock_tempdir,
        mock_getcwd,
        mock_chdir,
        mock_system,
        mock_sleep,
        nx_util,
    ):
        """Test show_html_temp functionality."""
        mock_getcwd.return_value = "/original/dir"
        mock_network = Mock()
        mock_network_class.return_value = mock_network

        # Mock temporary directory context manager
        mock_temp_context = MagicMock()
        mock_temp_context.__enter__.return_value = "/tmp/tempdir"
        mock_tempdir.return_value = mock_temp_context

        nx_util.show_html_temp()

        # Verify directory operations
        assert mock_chdir.call_count == 2
        mock_chdir.assert_any_call("/tmp/tempdir")
        mock_chdir.assert_any_call("/original/dir")

        # Verify network operations
        mock_network.write_html.assert_called_once_with(
            "temp.html", local=True, notebook=False
        )

        # Verify system calls
        mock_system.assert_called_once_with("open temp.html")
        mock_sleep.assert_called_once_with(5)

    def test_complex_graph(self):
        """Test with a more complex graph."""
        G = nx.DiGraph()
        # Add nodes with attributes
        G.add_node("root", label="Root Node")
        G.add_node("child1", label="Child 1")
        G.add_node("child2", label="Child 2")

        # Add edges with weights
        G.add_edge("root", "child1", weight=1.0)
        G.add_edge("root", "child2", weight=2.0)
        G.add_edge("child1", "child2", weight=0.5)

        util = NxGraphUtil(graph=G)
        assert util.graph.number_of_nodes() == 3
        assert util.graph.number_of_edges() == 3

    @patch("pinjected.nx_graph_util.Network")
    def test_empty_graph(self, mock_network_class):
        """Test with empty graph."""
        G = nx.DiGraph()
        util = NxGraphUtil(graph=G)

        mock_network = Mock()
        mock_network_class.return_value = mock_network

        result = util.to_physics_network()

        mock_network.from_nx.assert_called_once_with(G)
        assert result is mock_network


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
