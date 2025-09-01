# User Guide: IEC 62304 Compliant SOUP Management

## Overview

The enhanced SOUP (Software of Unknown Provenance) management system provides automated detection, classification, and compliance management for third-party software components according to IEC 62304 standards. This feature helps medical device manufacturers maintain regulatory compliance for all external software dependencies.

## What is SOUP?

**SOUP Definition (IEC 62304)**: Software of Unknown Provenance is software that was not developed for the purpose of being incorporated into the medical device (also known as "off-the-shelf software") or software previously developed for which adequate records of the development processes are not available.

### Examples of SOUP Components
- **JavaScript Libraries**: React, Express, Lodash, Moment.js
- **Python Packages**: NumPy, Pandas, Flask, Django
- **C/C++ Libraries**: OpenSSL, zlib, SQLite
- **Development Tools**: Compilers, build systems, testing frameworks
- **Operating System Components**: System libraries, drivers

## Key Features

### 1. Automated Detection
- **Multi-format Support**: Detects SOUP from package.json, requirements.txt, CMakeLists.txt, and more
- **Confidence Scoring**: Assigns confidence levels to detected components
- **Version Tracking**: Monitors version changes and updates
- **Dependency Analysis**: Identifies transitive dependencies

### 2. IEC 62304 Classification
- **Safety Class Assignment**: Automatic classification as Class A, B, or C
- **Justification Templates**: Pre-filled safety justification templates
- **Risk Assessment Integration**: Links SOUP components to risk analysis
- **Verification Requirements**: Generates verification activities based on classification

### 3. Compliance Management
- **Documentation Generation**: Creates IEC 62304 compliant SOUP lists
- **Change Impact Analysis**: Assesses impact of version changes
- **Audit Trail**: Maintains complete history of SOUP decisions
- **Regulatory Reporting**: Generates reports for regulatory submissions

## Accessing SOUP Management

### Navigation Steps

1. **Run Project Analysis**: Complete full project analysis
2. **Open Results Tab**: Navigate to main results area
3. **Select SOUP Tab**: Click on "SOUP Components" tab
4. **View Detected Components**: Review automatically detected SOUP

### SOUP Management Interface

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          SOUP Components                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ [Auto-Detect] [Add Manual] [Import] [Export] [Generate Report]             │
├─────────────────────────────────────────────────────────────────────────────┤
│ Component Name    │ Version │ Safety Class │ Confidence │ Status            │
├───────────────────┼─────────┼──────────────┼────────────┼───────────────────┤
│ express           │ 4.18.0  │ Class B      │ 0.95       │ ✓ Classified      │
│ lodash            │ 4.17.21 │ Class A      │ 0.90       │ ✓ Classified      │
│ numpy             │ 1.21.0  │ Class C      │ 0.85       │ ⚠ Needs Review   │
│ openssl           │ 1.1.1   │ Class C      │ 0.80       │ ❌ Incomplete     │
└───────────────────┴─────────┴──────────────┴────────────┴───────────────────┘
```

## Understanding IEC 62304 Safety Classifications

### Class A: Non-Safety Related
**Definition**: SOUP that cannot contribute to a hazardous situation

**Characteristics**:
- No impact on patient safety if it fails
- Failure does not affect medical device safety functions
- Used for non-critical functionality only

**Examples**:
- Logging libraries
- User interface styling components
- Development and testing tools
- Documentation generators

**Verification Requirements**:
- Basic functional testing
- License compliance verification
- Known anomaly documentation

### Class B: Non-Life-Threatening Safety Related
**Definition**: SOUP that can contribute to a hazardous situation but not death or serious injury

**Characteristics**:
- Failure could cause minor patient harm
- Affects device functionality but not life-critical operations
- Used in monitoring or alerting functions

**Examples**:
- Data validation libraries
- Communication protocols
- User interface frameworks
- Reporting components

**Verification Requirements**:
- Functional testing of safety-related features
- Integration testing with medical device functions
- Anomaly list review and impact assessment
- Change control procedures

### Class C: Life-Threatening Safety Related
**Definition**: SOUP that can contribute to death or serious injury

**Characteristics**:
- Failure could directly cause patient death or serious injury
- Critical to device safety functions
- Used in diagnostic, therapeutic, or life-support functions

**Examples**:
- Mathematical computation libraries (for dose calculations)
- Real-time operating systems
- Communication stacks for critical alarms
- Cryptographic libraries for security

**Verification Requirements**:
- Comprehensive functional testing
- Safety-focused integration testing
- Detailed anomaly analysis and mitigation
- Rigorous change control
- Supplier assessment and ongoing monitoring

## Working with SOUP Components

### Automatic Detection Process

The system automatically scans your project for SOUP components:

1. **File Analysis**: Scans dependency files (package.json, requirements.txt, etc.)
2. **Component Identification**: Identifies third-party components and versions
3. **Confidence Assessment**: Assigns confidence scores based on detection method
4. **Initial Classification**: Suggests safety classifications based on component type

### Manual Component Management

**Adding Components Manually**:
1. **Click "Add Manual"**: Opens component entry dialog
2. **Enter Component Details**:
   - Name and version
   - Supplier information
   - Intended use description
   - Source/origin details
3. **Assign Safety Classification**: Select Class A, B, or C
4. **Provide Justification**: Document classification rationale

**Editing Existing Components**:
1. **Double-click Component**: Opens detailed editor
2. **Modify Information**: Update any component details
3. **Review Classification**: Verify safety class is still appropriate
4. **Update Justification**: Revise documentation as needed

### Component Details Dialog

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SOUP Component Details                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ Component Name: [express                                    ]               │
│ Version:        [4.18.0                                    ]               │
│ Supplier:       [OpenJS Foundation                         ]               │
│ License:        [MIT                                       ]               │
│                                                                             │
│ Safety Classification: [Class B ▼]                                         │
│                                                                             │
│ Intended Use:                                                               │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ Web server framework for handling HTTP requests and routing in the      │ │
│ │ medical device's web interface. Used for non-critical user interface   │ │
│ │ functions and data presentation.                                        │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ Safety Justification:                                                       │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ Classified as Class B because failure could affect user interface       │ │
│ │ functionality and potentially delay clinical decision-making, but       │ │
│ │ cannot directly cause death or serious injury. The medical device       │ │
│ │ has independent safety mechanisms that do not rely on the web interface.│ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ Known Anomalies:                                                            │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ • CVE-2022-24999: Potential DoS vulnerability (mitigated by firewall)  │ │
│ │ • Performance degradation under high load (acceptable for use case)    │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ Verification Activities:                                                    │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ • Functional testing of web interface components                        │ │
│ │ • Integration testing with medical device backend                       │ │
│ │ • Security vulnerability assessment                                     │ │
│ │ • Performance testing under expected load conditions                    │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ [Save] [Cancel] [Generate Verification Plan]                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Compliance Documentation

### SOUP List Generation

The system generates comprehensive SOUP documentation:

**IEC 62304 SOUP List Contents**:
- Component identification and version
- Supplier information and contact details
- Intended use within the medical device
- Safety classification and justification
- Known anomalies and their impact assessment
- Verification and validation activities
- Change control procedures

### Documentation Templates

**Class A Template**:
```
SOUP Component: [Component Name] v[Version]
Safety Classification: Class A (Non-Safety Related)

Intended Use:
[Description of how component is used in non-safety functions]

Justification for Class A:
This component is classified as Class A because:
• It is used only for [non-safety function]
• Failure cannot contribute to a hazardous situation
• No patient safety impact if component fails
• [Additional specific justifications]

Verification Activities:
• Basic functional testing
• License compliance verification
• Documentation of known anomalies
```

**Class B Template**:
```
SOUP Component: [Component Name] v[Version]
Safety Classification: Class B (Non-Life-Threatening Safety Related)

Intended Use:
[Description of safety-related but non-life-threatening use]

Justification for Class B:
This component is classified as Class B because:
• Used in safety-related functions: [specific functions]
• Failure could contribute to hazardous situation but not death/serious injury
• Impact limited to: [specific impact description]
• Mitigation measures in place: [describe mitigations]

Verification Activities:
• Functional testing of safety-related features
• Integration testing with medical device safety functions
• Anomaly list review and impact assessment
• Supplier evaluation and ongoing monitoring
```

**Class C Template**:
```
SOUP Component: [Component Name] v[Version]
Safety Classification: Class C (Life-Threatening Safety Related)

Intended Use:
[Description of life-critical use within medical device]

Justification for Class C:
This component is classified as Class C because:
• Used in life-critical functions: [specific functions]
• Failure could directly contribute to death or serious injury
• Critical to: [specific safety functions]
• No alternative implementation available

Risk Mitigation:
• [Specific risk mitigation measures]
• [Redundancy or backup systems]
• [Monitoring and detection mechanisms]

Verification Activities:
• Comprehensive functional testing of all safety-critical features
• Extensive integration testing with medical device safety systems
• Detailed anomaly analysis and mitigation verification
• Supplier assessment and qualification
• Ongoing monitoring and change control
• Independent safety assessment
```

## Change Management

### Version Change Detection

The system monitors SOUP components for version changes:

**Automatic Detection**:
- Scans dependency files during each analysis
- Identifies version updates, additions, and removals
- Flags changes for review and impact assessment

**Change Impact Assessment**:
1. **Identify Changes**: List all component modifications
2. **Assess Safety Impact**: Evaluate effect on safety classification
3. **Review Anomalies**: Check for new known issues
4. **Update Documentation**: Revise SOUP documentation as needed
5. **Plan Verification**: Define additional testing if required

### Change Control Process

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SOUP Change Control                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ Change Detected: express v4.17.1 → v4.18.0                                │
│                                                                             │
│ Change Type: [Minor Version Update ▼]                                      │
│                                                                             │
│ Impact Assessment:                                                          │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │ • Security patches included (CVE-2022-24999 fixed)                     │ │
│ │ • Performance improvements in routing                                   │ │
│ │ • No breaking changes to API                                           │ │
│ │ • Safety classification remains Class B                                │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ Required Actions:                                                           │
│ ☐ Update SOUP documentation                                                │
│ ☐ Perform regression testing                                               │
│ ☐ Verify security vulnerability fix                                        │
│ ☐ Update anomaly list                                                      │
│                                                                             │
│ Approval Required: [Yes ▼] Approver: [Quality Manager ▼]                  │
│                                                                             │
│ [Approve Change] [Reject Change] [Request More Info]                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Export and Reporting

### Export Formats

**1. IEC 62304 SOUP List (PDF)**
- Regulatory-compliant format
- Professional layout for submissions
- Includes all required IEC 62304 elements
- Signature pages for approval

**2. Excel Spreadsheet**
- Sortable and filterable data
- Conditional formatting for status indicators
- Multiple worksheets for different views
- Formulas for automatic calculations

**3. CSV Data Export**
- Raw data for external processing
- Integration with other tools
- Bulk data manipulation
- Database import format

**4. JSON Structured Data**
- API integration format
- Automated processing
- Configuration management
- Tool interoperability

### Regulatory Reports

**FDA 510(k) SOUP Documentation**:
- Complete SOUP inventory
- Safety classification justifications
- Verification and validation evidence
- Change control documentation

**EU MDR Technical Documentation**:
- SOUP risk assessment
- Post-market surveillance plan
- Software lifecycle documentation
- Conformity assessment evidence

## Best Practices

### Classification Guidelines

**Systematic Approach**:
1. **Identify Function**: Determine how SOUP is used in device
2. **Assess Failure Impact**: Evaluate consequences of SOUP failure
3. **Consider Mitigations**: Account for existing safety measures
4. **Document Rationale**: Provide clear justification for classification
5. **Review Regularly**: Reassess classification when usage changes

**Common Classification Scenarios**:

| SOUP Type | Typical Use | Suggested Class | Rationale |
|-----------|-------------|-----------------|-----------|
| UI Framework | User interface | Class A or B | Depends on criticality of UI functions |
| Math Library | Calculations | Class B or C | Depends on calculation criticality |
| Database | Data storage | Class B | Data integrity affects device function |
| Crypto Library | Security | Class C | Security failures can be life-threatening |
| Logging | Audit trail | Class A | Logging failure doesn't affect safety |

### Documentation Quality

**Complete Documentation**:
- Detailed intended use descriptions
- Specific safety justifications
- Comprehensive anomaly lists
- Clear verification plans

**Regular Updates**:
- Review SOUP list quarterly
- Update after any component changes
- Reassess classifications annually
- Maintain change history

### Supplier Management

**Supplier Evaluation**:
- Assess supplier quality processes
- Evaluate support and maintenance commitments
- Review security practices
- Establish communication channels

**Ongoing Monitoring**:
- Subscribe to security advisories
- Monitor for new anomalies
- Track supplier stability
- Plan for end-of-life scenarios

## Troubleshooting

### Common Issues

**Components Not Detected**
- **Check File Formats**: Ensure dependency files are in supported formats
- **Verify File Locations**: Confirm files are in expected project locations
- **Review Parsing Logs**: Check for parsing errors in application logs

**Incorrect Classifications**
- **Review Usage Context**: Ensure classification reflects actual device usage
- **Consider Failure Modes**: Evaluate all possible failure scenarios
- **Consult Standards**: Reference IEC 62304 guidance documents
- **Seek Expert Review**: Have safety engineers review classifications

**Export Failures**
- **Check Permissions**: Ensure write access to destination folder
- **Verify Data Completeness**: Confirm all required fields are populated
- **Review File Size**: Large SOUP lists may need special handling

**Performance Issues**
- **Filter Components**: Work with subsets for large SOUP inventories
- **Batch Operations**: Process changes in smaller groups
- **Background Processing**: Allow detection to complete before viewing results

This comprehensive SOUP management system ensures IEC 62304 compliance while streamlining the documentation and maintenance of third-party software components in medical devices.