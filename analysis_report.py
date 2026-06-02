#!/usr/bin/env python3
"""
Comprehensive analysis of poker_trainer.py for data consistency and completeness.
"""

import re
import sys
from collections import defaultdict

# ============================================================
# CONSTANTS FOR VALIDATION
# ============================================================
VALID_RANKS = set('23456789TJQKA')
VALID_SUITS = set(['♥', '♦', '♣', '♠'])  # Unicode suits
VALID_NOTATION_PATTERN = re.compile(r'^[23456789TJQKA]{2}[so]?$')

def is_valid_hand_notation(hand):
    """Check if hand notation is valid poker notation."""
    if not hand or not isinstance(hand, str):
        return False
    # Valid: AA, AKo, AKs, etc.
    if len(hand) < 2 or len(hand) > 3:
        return False
    r1, r2 = hand[0], hand[1]
    if r1 not in VALID_RANKS or r2 not in VALID_RANKS:
        return False
    if len(hand) == 3:
        suffix = hand[2]
        if suffix not in ['s', 'o']:
            return False
    return True

def analyze_poker_trainer():
    """Main analysis function."""
    
    print("=" * 80)
    print("POKER TRAINER ANALYSIS REPORT")
    print("=" * 80)
    
    errors = []
    warnings = []
    info_messages = []
    
    # Read the file
    try:
        with open('c:/Users/DELL/Desktop/PP/poker_trainer.py', 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"ERROR: Could not read file: {e}")
        return
    
    # Extract SPIN_CATEGORIES
    spin_match = re.search(r'SPIN_CATEGORIES\s*=\s*(\{[^}]+?\n\})', content, re.DOTALL)
    spin_categories_lines = []
    spin_spots_by_category = {}
    
    if spin_match:
        spin_text = spin_match.group(1)
        spin_spots_by_category = extract_categories(spin_text)
        for cat, spots in spin_spots_by_category.items():
            info_messages.append(f"SPIN_CATEGORIES['{cat}']: {len(spots)} spots")
    
    # Extract HU_CATEGORIES
    hu_match = re.search(r'HU_CATEGORIES\s*=\s*(\{[^}]+?\n\})', content, re.DOTALL)
    hu_spots_by_category = {}
    
    if hu_match:
        hu_text = hu_match.group(1)
        hu_spots_by_category = extract_categories(hu_text)
        for cat, spots in hu_spots_by_category.items():
            info_messages.append(f"HU_CATEGORIES['{cat}']: {len(spots)} spots")
    
    # Extract all CHARTS keys
    charts_spots = set()
    charts_match = re.search(r'CHARTS\s*=\s*\{', content)
    if charts_match:
        start = charts_match.end()
        # Find all quoted keys that appear to be chart names
        remaining = content[start:]
        # Extract all keys from CHARTS dictionary
        chart_keys = re.findall(r'"([^"]+)"\s*:\s*\{', remaining)
        for i, key in enumerate(chart_keys):
            # Stop when we hit HU_CHARTS
            if key.startswith('HU'):
                break
            charts_spots.add(key)
    
    # Extract all HU_CHARTS keys
    hu_charts_spots = set()
    hu_charts_match = re.search(r'HU_CHARTS\s*=\s*\{', content)
    if hu_charts_match:
        start = hu_charts_match.end()
        # Find the end of HU_CHARTS by looking for the next top-level variable or function
        end_match = re.search(r'\n# .*?ORGANIZATION|LOGIC|\Z', content[start:], re.MULTILINE)
        end = start + end_match.end() if end_match else len(content)
        
        hu_section = content[start:end]
        hu_chart_keys = re.findall(r'"([^"]+)"\s*:\s*\{', hu_section)
        for key in hu_chart_keys:
            hu_charts_spots.add(key)
    
    print(f"\n✓ Found {len(charts_spots)} SPIN spots in CHARTS dictionary")
    print(f"✓ Found {len(hu_charts_spots)} HU spots in HU_CHARTS dictionary")
    
    # ========================================================
    # CHECK 1: All SPIN_CATEGORIES spots in CHARTS
    # ========================================================
    print("\n" + "=" * 80)
    print("CHECK 1: SPIN_CATEGORIES Spots Coverage")
    print("=" * 80)
    
    all_spin_spots = set()
    for category, spots in spin_spots_by_category.items():
        all_spin_spots.update(spots)
    
    missing_in_charts = all_spin_spots - charts_spots
    if missing_in_charts:
        for spot in sorted(missing_in_charts):
            errors.append(f"CHARTS: Missing spot '{spot}' (defined in SPIN_CATEGORIES)")
        print(f"✗ {len(missing_in_charts)} spots missing from CHARTS")
        for spot in sorted(missing_in_charts):
            print(f"  - {spot}")
    else:
        print("✓ All SPIN_CATEGORIES spots are present in CHARTS")
    
    # ========================================================
    # CHECK 2: All HU_CATEGORIES spots in HU_CHARTS
    # ========================================================
    print("\n" + "=" * 80)
    print("CHECK 2: HU_CATEGORIES Spots Coverage")
    print("=" * 80)
    
    all_hu_spots = set()
    for category, spots in hu_spots_by_category.items():
        all_hu_spots.update(spots)
    
    missing_in_hu_charts = all_hu_spots - hu_charts_spots
    if missing_in_hu_charts:
        for spot in sorted(missing_in_hu_charts):
            errors.append(f"HU_CHARTS: Missing spot '{spot}' (defined in HU_CATEGORIES)")
        print(f"✗ {len(missing_in_hu_charts)} spots missing from HU_CHARTS")
        for spot in sorted(missing_in_hu_charts):
            print(f"  - {spot}")
    else:
        print("✓ All HU_CATEGORIES spots are present in HU_CHARTS")
    
    # ========================================================
    # CHECK 3: Duplicate spot names
    # ========================================================
    print("\n" + "=" * 80)
    print("CHECK 3: Duplicate Spot Names")
    print("=" * 80)
    
    duplicate_spots = all_spin_spots & all_hu_spots
    if duplicate_spots:
        for spot in sorted(duplicate_spots):
            errors.append(f"Duplicate spot name: '{spot}' appears in both SPIN and HU categories")
        print(f"✗ {len(duplicate_spots)} duplicate spot names found")
        for spot in sorted(duplicate_spots):
            print(f"  - {spot}")
    else:
        print("✓ No duplicate spot names found")
    
    # ========================================================
    # CHECK 4: Chart structure validation
    # ========================================================
    print("\n" + "=" * 80)
    print("CHECK 4: Chart Structure Validation")
    print("=" * 80)
    
    # Parse each chart to validate structure
    all_spot_names = all_spin_spots | hu_charts_spots
    charts_to_check = all_spot_names  # Check all spots
    
    struct_issues = validate_chart_structures(content, charts_to_check)
    if struct_issues:
        for issue in struct_issues:
            errors.append(issue)
        print(f"✗ {len(struct_issues)} structural issues found")
        for issue in struct_issues[:20]:  # Show first 20
            print(f"  - {issue}")
        if len(struct_issues) > 20:
            print(f"  ... and {len(struct_issues) - 20} more")
    else:
        print("✓ All charts have valid structure (type, data, buttons)")
    
    # ========================================================
    # CHECK 5: EVERYTHING_ELSE handling
    # ========================================================
    print("\n" + "=" * 80)
    print("CHECK 5: EVERYTHING_ELSE Handling")
    print("=" * 80)
    
    everything_else_issues = validate_everything_else(content, all_spot_names)
    if everything_else_issues:
        for issue in everything_else_issues:
            warnings.append(issue)
        print(f"⚠ {len(everything_else_issues)} EVERYTHING_ELSE issues found")
        for issue in everything_else_issues[:15]:
            print(f"  - {issue}")
        if len(everything_else_issues) > 15:
            print(f"  ... and {len(everything_else_issues) - 15} more")
    else:
        print("✓ EVERYTHING_ELSE usage appears correct")
    
    # ========================================================
    # CHECK 6: Hand notation validation
    # ========================================================
    print("\n" + "=" * 80)
    print("CHECK 6: Hand Notation Consistency")
    print("=" * 80)
    
    hand_notation_issues = validate_hand_notations(content, all_spot_names)
    if hand_notation_issues:
        for issue in hand_notation_issues:
            warnings.append(issue)
        print(f"⚠ {len(hand_notation_issues)} invalid hand notations found")
        for issue in hand_notation_issues[:20]:
            print(f"  - {issue}")
        if len(hand_notation_issues) > 20:
            print(f"  ... and {len(hand_notation_issues) - 20} more")
    else:
        print("✓ All hand notations are valid")
    
    # ========================================================
    # SUMMARY
    # ========================================================
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nTotal SPIN spots: {len(all_spin_spots)}")
    print(f"Total HU spots: {len(all_hu_spots)}")
    print(f"Total unique spots: {len(all_spin_spots | all_hu_spots)}")
    
    print(f"\n✗ ERRORS: {len(errors)}")
    if errors:
        for i, err in enumerate(errors, 1):
            print(f"  {i}. {err}")
    
    print(f"\n⚠ WARNINGS: {len(warnings)}")
    if warnings:
        for i, warn in enumerate(warnings, 1):
            print(f"  {i}. {warn}")
    
    print(f"\n✓ INFO: {len(info_messages)}")
    if info_messages:
        for msg in info_messages[:10]:
            print(f"  - {msg}")
    
    # Final status
    print("\n" + "=" * 80)
    if errors:
        print("STATUS: ✗ ISSUES FOUND - Please fix the errors above")
        return False
    elif warnings:
        print("STATUS: ⚠ WARNINGS ONLY - No critical errors, but review warnings")
        return True
    else:
        print("STATUS: ✓ ALL CHECKS PASSED")
        return True

def extract_categories(text):
    """Extract categories from the SPIN_CATEGORIES or HU_CATEGORIES text."""
    categories = {}
    lines = text.split('\n')
    current_category = None
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Look for category definition: "CATEGORY": [
        cat_match = re.match(r'"([^"]+)"\s*:\s*\[', line)
        if cat_match:
            current_category = cat_match.group(1)
            categories[current_category] = []
            
            # Extract spots from this line or following lines
            bracket_content = line[line.index('[')+1:]
            if ']' in bracket_content:
                # All on one line
                bracket_content = bracket_content[:bracket_content.index(']')]
            
            spots = extract_spots_from_bracket(bracket_content)
            categories[current_category].extend(spots)
        
        elif current_category and line.startswith('"'):
            # Continuation of previous category
            bracket_content = line
            if ']' in bracket_content:
                bracket_content = bracket_content[:bracket_content.index(']')]
            
            spots = extract_spots_from_bracket(bracket_content)
            categories[current_category].extend(spots)
    
    return categories

def extract_spots_from_bracket(text):
    """Extract spot names from bracket content."""
    spots = []
    # Find all quoted strings
    matches = re.findall(r'"([^"]+)"', text)
    for match in matches:
        if match not in ['', ' ']:
            spots.append(match)
    return spots

def validate_chart_structures(content, spot_names):
    """Validate that each chart has type, data, and buttons."""
    issues = []
    
    # For each spot, try to find its chart definition
    for spot in sorted(spot_names):
        # Find the chart definition
        pattern = f'"{re.escape(spot)}"' + r'\s*:\s*\{([^}]*?"buttons":[^}]*?)\}'
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            issues.append(f"Chart not found or incomplete: {spot}")
            continue
        
        chart_content = match.group(1)
        
        # Check for required keys
        has_type = '"type"' in chart_content
        has_data = '"data"' in chart_content
        has_buttons = '"buttons"' in chart_content
        
        if not has_type:
            issues.append(f"{spot}: Missing 'type' key")
        if not has_data:
            issues.append(f"{spot}: Missing 'data' key")
        if not has_buttons:
            issues.append(f"{spot}: Missing 'buttons' key")
    
    return issues

def validate_everything_else(content, spot_names):
    """Check EVERYTHING_ELSE usage."""
    issues = []
    everything_else_pattern = re.compile(r'"([^"]+)"\s*:\s*"EVERYTHING_ELSE"')
    
    for spot in sorted(spot_names):
        pattern = f'"{re.escape(spot)}"' + r'\s*:\s*\{([^}]*?)\}'
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            continue
        
        chart_content = match.group(1)
        
        # Check if EVERYTHING_ELSE is used in data section
        data_match = re.search(r'"data"\s*:\s*\{([^}]*?)\}', chart_content, re.DOTALL)
        if data_match:
            data_section = data_match.group(1)
            everything_else_count = data_section.count('EVERYTHING_ELSE')
            
            if everything_else_count == 0:
                # Check if all possible hands are covered (optional check)
                pass
            elif everything_else_count > 1:
                issues.append(f"{spot}: Multiple EVERYTHING_ELSE entries in data (should be 1)")
    
    return issues

def validate_hand_notations(content, spot_names):
    """Validate that all hand notations are correct."""
    issues = []
    invalid_hands_found = defaultdict(list)
    
    for spot in sorted(spot_names):
        pattern = f'"{re.escape(spot)}"' + r'\s*:\s*\{([^}]*?)\}'
        match = re.search(pattern, content, re.DOTALL)
        
        if not match:
            continue
        
        chart_content = match.group(1)
        
        # Extract all quoted strings that look like hand notations
        potential_hands = re.findall(r'"([A-Za-z0-9]{2,3})"', chart_content)
        
        for hand in potential_hands:
            if hand in ['type', 'data', 'buttons', 'categorical', 'numerical', 'All in', 'Fold', 'Call', 
                       'Check', 'Raise', 'Limp', 'raises', 'calls', 'folds', 'checks', 'posts', 'bets',
                       'EVERYTHING_ELSE', 'and', 'is', 'or', 'PREFLOP', 'FLOP', 'TURN', 'RIVER']:
                continue
            
            if not is_valid_hand_notation(hand):
                invalid_hands_found[spot].append(hand)
    
    for spot, hands in sorted(invalid_hands_found.items()):
        unique_hands = set(hands)
        for hand in sorted(unique_hands):
            issues.append(f"{spot}: Invalid hand notation: '{hand}'")
    
    return issues

if __name__ == "__main__":
    success = analyze_poker_trainer()
    sys.exit(0 if success else 1)
