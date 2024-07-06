import os
import platform
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import networkx as nx
from loguru import logger
from networkx.drawing.nx_agraph import graphviz_layout
from pyvis.network import Network


@dataclass
class NxGraphUtil:
    graph: nx.DiGraph
    def to_physics_network(self):
        nt = Network('1080px', '100%', directed=True)
        nt.from_nx(self.graph)
        nt.toggle_physics(True)
        return nt

    def plot_mpl(self):
        from matplotlib import pyplot as plt
        G = self.graph
        plt.figure(figsize=(20, 20))
        pos = graphviz_layout(G, prog='dot')
        nx.draw(G, with_labels=True, pos=pos)
        plt.show()

    def save_as_html(self,name:str,show=True):
        assert isinstance(name,str)
        self.to_physics_network().show(name)
        if "darwin" in platform.system().lower() and show:
            os.system(f"open {name}")

    def save_as_html_at(self,dst_dir:Path):
        assert isinstance(dst_dir,Path)
        dst_dir.mkdir(parents=True,exist_ok=True)
        org_dir = os.getcwd()
        os.chdir(dst_dir)
        self.to_physics_network().write_html("graph.html",local=True,notebook=False)
        os.chdir(org_dir)
        return dst_dir/"graph.html"



    def show_html(self):
        if "darwin" in platform.system().lower():
            from loguru import logger
            logger.info(f"showing visualization html")
            self.save_as_html("di_visualiztion.html")
            os.system("open di_visualiztion.html")
        else:
            from loguru import logger
            logger.warning("visualization of a design is disabled for non mac os.")

    def show_html_temp(self):
        org_dir = os.getcwd()
        nt = self.to_physics_network()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            temp_file_path = "temp.html"
            nt.write_html(temp_file_path, local=True, notebook=False)
            os.system(f"open {temp_file_path}")
            time.sleep(5)
        os.chdir(org_dir)