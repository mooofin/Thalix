"""
Cheat Engine Integration Module
Allows loading and using existing Cheat Engine (.ct) cheat tables
"""

import xml.etree.ElementTree as ET
import json
import os
import logging
import subprocess
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class CheatEngineTable:
    """Parse and manage Cheat Engine (.ct) table files"""
    
    def __init__(self):
        self.entries = []
        self.file_path = None
        self.game_name = None
        
    def load_ct_file(self, file_path: str) -> bool:
        """Load a Cheat Engine .ct file"""
        try:
            logger.info(f"Loading Cheat Engine table: {file_path}")
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            self.file_path = file_path
            self.entries = []
            
            # Find CheatTable element
            cheat_table = root.find('CheatTable')
            if cheat_table is None:
                cheat_table = root
            
            # Parse cheat entries
            cheat_entries = cheat_table.find('CheatEntries')
            if cheat_entries is not None:
                for entry in cheat_entries.findall('CheatEntry'):
                    parsed_entry = self._parse_entry(entry)
                    if parsed_entry:
                        self.entries.append(parsed_entry)
            
            logger.info(f"Loaded {len(self.entries)} cheat entries from {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load Cheat Engine table: {e}")
            return False
    
    def _parse_entry(self, entry: ET.Element) -> Optional[Dict[str, Any]]:
        """Parse a single cheat entry from XML"""
        try:
            description = entry.find('Description')
            desc_text = description.text if description is not None else "Unknown"
            
            # Check if it's a group header
            options = entry.find('Options')
            if options is not None and options.get('moHideChildren') == '1':
                return {
                    'type': 'group',
                    'description': desc_text,
                    'children': []
                }
            
            # Parse address
            address_elem = entry.find('Address')
            address_str = address_elem.text if address_elem is not None else None
            
            # Parse variable type
            var_type = entry.find('VariableType')
            var_type_str = var_type.text if var_type is not None else "4 Bytes"
            
            # Convert Cheat Engine type to our format
            type_mapping = {
                'Byte': 'byte',
                '2 Bytes': 'short',
                '4 Bytes': 'int',
                '8 Bytes': 'long',
                'Float': 'float',
                'Double': 'double',
                'String': 'string',
                'Array of byte': 'bytes'
            }
            
            value_type = type_mapping.get(var_type_str, 'int')
            
            # Parse offsets for pointer chains
            offsets = []
            offsets_elem = entry.find('Offsets')
            if offsets_elem is not None:
                for offset in offsets_elem.findall('Offset'):
                    if offset.text:
                        try:
                            offsets.append(int(offset.text, 16))
                        except:
                            pass
            
            # Parse hotkeys
            hotkeys_elem = entry.find('Hotkeys')
            hotkeys = []
            if hotkeys_elem is not None:
                for hotkey in hotkeys_elem.findall('Hotkey'):
                    action = hotkey.find('Action')
                    keys = hotkey.find('Keys')
                    if action is not None and keys is not None:
                        hotkeys.append({
                            'action': action.text,
                            'keys': keys.text
                        })
            
            return {
                'type': 'entry',
                'description': desc_text,
                'address': address_str,
                'value_type': value_type,
                'offsets': offsets,
                'hotkeys': hotkeys,
                'enabled': False,
                'frozen': False
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse entry: {e}")
            return None
    
    def save_to_json(self, output_path: str) -> bool:
        """Save parsed entries to JSON format"""
        try:
            with open(output_path, 'w') as f:
                json.dump({
                    'game': self.game_name,
                    'source_file': self.file_path,
                    'entries': self.entries
                }, f, indent=2)
            logger.info(f"Saved cheat table to JSON: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save to JSON: {e}")
            return False
    
    def get_entries_by_type(self, entry_type: str = 'entry') -> List[Dict]:
        """Get all entries of a specific type"""
        return [e for e in self.entries if e.get('type') == entry_type]
    
    def search_entries(self, keyword: str) -> List[Dict]:
        """Search entries by description"""
        keyword_lower = keyword.lower()
        return [e for e in self.entries 
                if keyword_lower in e.get('description', '').lower()]


class CheatEngineIntegration:
    """Integration layer between Cheat Engine tables and Thalix memory editor"""
    
    def __init__(self, memory_editor):
        self.memory_editor = memory_editor
        self.current_table = None
        self.active_cheats = {}  # Track active/frozen cheats

    def launch_external_cheat_engine(self, ce_exe_path: str, ct_file: Optional[str] = None) -> bool:
        """Launch an external Cheat Engine executable optionally opening a .ct file.

        This will simply spawn the provided executable with the cheat table path
        as an argument. It does not attempt to embed Cheat Engine into this
        application. Returns True on successful spawn, False otherwise.
        """
        try:
            if not ce_exe_path:
                logger.error("No Cheat Engine executable path provided")
                return False

            if not os.path.exists(ce_exe_path):
                logger.error(f"Cheat Engine executable not found: {ce_exe_path}")
                return False

            args = [ce_exe_path]
            if ct_file:
                # If file is not absolute, leave it as-is; OS will resolve relative paths
                args.append(ct_file)

            # Use Popen so the GUI stays responsive and we don't block
            subprocess.Popen(args, shell=False)
            logger.info(f"Launched Cheat Engine: {ce_exe_path} with table: {ct_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to launch Cheat Engine: {e}")
            return False
        
    def load_cheat_table(self, file_path: str) -> bool:
        """Load a Cheat Engine table file"""
        table = CheatEngineTable()
        if table.load_ct_file(file_path):
            self.current_table = table
            return True
        return False
    
    def resolve_address(self, entry: Dict) -> Optional[int]:
        """Resolve an address, including pointer chains"""
        try:
            address_str = entry.get('address')
            if not address_str:
                return None
            
            # Simple address (hex)
            if address_str.startswith('0x') or address_str.isdigit():
                base_addr = int(address_str, 16) if address_str.startswith('0x') else int(address_str)
            else:
                # Complex address like "[module+offset]"
                # For now, just try to parse as hex
                try:
                    base_addr = int(address_str.replace('[', '').replace(']', '').split('+')[1], 16)
                except:
                    logger.warning(f"Cannot parse address: {address_str}")
                    return None
            
            # Apply pointer chain if offsets exist
            offsets = entry.get('offsets', [])
            if offsets and self.memory_editor:
                return self.memory_editor.read_pointer_chain(base_addr, offsets)
            
            return base_addr
            
        except Exception as e:
            logger.error(f"Failed to resolve address: {e}")
            return None
    
    def read_value(self, entry: Dict) -> Optional[Any]:
        """Read value for a cheat entry"""
        if not self.memory_editor:
            return None
            
        address = self.resolve_address(entry)
        if address is None:
            return None
        
        value_type = entry.get('value_type', 'int')
        
        try:
            if value_type == 'byte':
                data = self.memory_editor.read_memory(address, 1)
                return int.from_bytes(data, 'little') if data else None
            elif value_type == 'short':
                data = self.memory_editor.read_memory(address, 2)
                return int.from_bytes(data, 'little') if data else None
            elif value_type == 'int':
                return self.memory_editor.read_int(address)
            elif value_type == 'long':
                return self.memory_editor.read_long(address)
            elif value_type == 'float':
                return self.memory_editor.read_float(address)
            elif value_type == 'double':
                return self.memory_editor.read_double(address)
            else:
                return None
        except Exception as e:
            logger.error(f"Failed to read value: {e}")
            return None
    
    def write_value(self, entry: Dict, value: Any) -> bool:
        """Write value for a cheat entry"""
        if not self.memory_editor:
            return False
            
        address = self.resolve_address(entry)
        if address is None:
            return False
        
        value_type = entry.get('value_type', 'int')
        
        try:
            if value_type == 'byte':
                data = int(value).to_bytes(1, 'little')
                return self.memory_editor.write_memory(address, data)
            elif value_type == 'short':
                data = int(value).to_bytes(2, 'little')
                return self.memory_editor.write_memory(address, data)
            elif value_type == 'int':
                return self.memory_editor.write_int(address, int(value))
            elif value_type == 'long':
                return self.memory_editor.write_long(address, int(value))
            elif value_type == 'float':
                return self.memory_editor.write_float(address, float(value))
            elif value_type == 'double':
                return self.memory_editor.write_double(address, float(value))
            else:
                return False
        except Exception as e:
            logger.error(f"Failed to write value: {e}")
            return False
    
    def freeze_value(self, entry: Dict, value: Any, memory_freezer) -> bool:
        """Freeze a value using the memory freezer"""
        address = self.resolve_address(entry)
        if address is None:
            return False
        
        value_type = entry.get('value_type', 'int')
        memory_freezer.add_frozen_address(address, value, value_type)
        
        self.active_cheats[entry['description']] = {
            'entry': entry,
            'address': address,
            'value': value,
            'frozen': True
        }
        
        return True
    
    def unfreeze_value(self, entry: Dict, memory_freezer) -> bool:
        """Unfreeze a value"""
        address = self.resolve_address(entry)
        if address is None:
            return False
        
        memory_freezer.remove_frozen_address(address)
        
        if entry['description'] in self.active_cheats:
            del self.active_cheats[entry['description']]
        
        return True
    
    def get_all_entries(self) -> List[Dict]:
        """Get all cheat entries from current table"""
        if self.current_table:
            return self.current_table.entries
        return []


def convert_ct_to_json(ct_file_path: str, json_output_path: str) -> bool:
    """Utility function to convert .ct file to JSON format"""
    table = CheatEngineTable()
    if table.load_ct_file(ct_file_path):
        return table.save_to_json(json_output_path)
    return False
