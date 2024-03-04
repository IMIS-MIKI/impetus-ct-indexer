from fhir.resources.bundle import Bundle, BundleEntry, BundleEntryRequest
from fhir.resources.patient import Patient
from fhir.resources.identifier import Identifier
from fhir.resources.provenance import Provenance
from fhir.resources.device import Device, DeviceVersion
from fhir.resources.bodystructure import BodyStructure, BodyStructureIncludedStructure
from fhir.resources.imagingstudy import ImagingStudy, ImagingStudySeries
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.reference import Reference
from fhir.resources.codeablereference import CodeableReference
from dotenv import load_dotenv

import os
import uuid
import snomed_ct_mapping


load_dotenv(verbose=True)

resource_uuids = {"patient": str(uuid.uuid4()), "series": str(uuid.uuid4()), "body_structure": str(uuid.uuid4()),
                  "device": str(uuid.uuid4())}


def transform_to_fhir(incoming):
    bundle = Bundle.construct()
    bundle.type = 'transaction'

    pat = create_patient(incoming['identification'])
    body_structure = create_body_structure(incoming['labels'])
    device = create_device(incoming['provenance'])
    study = create_imaging_study(incoming['identification'])

    pat_entry_request = BundleEntryRequest.construct(url='Patient', method='POST')
    pat_entry_request.ifNoneExist = "identifier=" + pat.identifier[0].system + "|" + pat.identifier[0].value

    device_entry_request = BundleEntryRequest.construct(url='Device', method='POST')
    device_entry_request.ifNoneExist = "identifier=" + device.identifier[0].system + "|" + device.identifier[0].value

    body_structure_request = BundleEntryRequest.construct(url='BodyStructure', method='POST')
    study_request = BundleEntryRequest.construct(url='ImagingStudy', method='POST')

    pat_entry = BundleEntry.construct()
    pat_entry.resource = pat
    pat_entry.request = pat_entry_request
    pat_entry.fullUrl = resource_uuids['patient']

    body_structure_entry = BundleEntry.construct()
    body_structure_entry.resource = body_structure
    body_structure_entry.request = body_structure_request
    body_structure_entry.fullUrl = resource_uuids['body_structure']

    device_entry = BundleEntry.construct()
    device_entry.resource = device
    device_entry.request = device_entry_request
    device_entry.fullUrl = resource_uuids['body_structure']

    study_entry = BundleEntry.construct()
    study_entry.resource = study
    study_entry.request = study_request
    study_entry.fullUrl = resource_uuids['series']

    bundle.entry = [pat_entry, body_structure_entry, study_entry, device_entry]

    print(bundle.json(indent=2))
    return bundle


def create_patient(pat_data):
    pat = Patient.construct()
    pat.active = True
    identifier = Identifier.construct()
    identifier.system = "https://mpi.medic.uksh.de/fhir"
    identifier.value = pat_data['mpi']
    pat.identifier = [identifier]
    return pat


def create_body_structure_concept(label):
    structure = CodeableConcept.construct()
    structure.coding = [snomed_ct_mapping.mapping.get(label)]
    return structure


def create_body_structure(labels):
    body_structure = BodyStructure.construct()
    body_structure.active = True
    body_structure.includedStructure = list()
    for label in labels:
        incl = BodyStructureIncludedStructure.construct()
        incl.structure = create_body_structure_concept(label)
        body_structure.includedStructure.append(incl)
    return body_structure


def create_device(prov_data):
    device = Device.construct()
    device.displayName = "IMPETUS CT-Indexer"
    device.status = "active"

    ident = Identifier.construct()
    ident.system = "https://ct-indexer.medic.uksh.de/fhir/version"
    ident.value = os.environ['VERSION']
    device.identifier = [ident]

    device_version_type = CodeableConcept.construct()
    device_version_type.coding = list()
    device_version_type.coding.append(
        {"system": "urn:iso:std:iso:11073:10101", "code": "531975", "display": "Software revision"})

    device_versions = []
    for key in prov_data.keys():
        device_version = DeviceVersion.construct()
        device_version.value = prov_data[key]
        device_version.type = device_version_type
        device_version.component = create_device_version_identifier(key)
        device_versions.append(device_version)
    device.version = device_versions
    return device


def create_device_version_identifier(value):
    version = Identifier.construct()
    version.system = "https://ct-indexer.medic.uksh.de/fhir/dependencies"
    version.value = value
    return version


def create_provenance(instant):
    prov = Provenance.construct()

    body_structure_ref = Reference.construct()
    body_structure_ref.reference = resource_uuids['body_structure']
    prov.target = [body_structure_ref]
    prov.recorded = instant
    return prov


def create_imaging_study(img_data):
    study = ImagingStudy.construct()
    study.status = 'available'

    pat_ref = Reference.construct()
    pat_ref.reference = resource_uuids['patient']
    study.subject = pat_ref

    series = ImagingStudySeries.construct()
    series.uid = img_data['series']

    body_structure_ref = Reference.construct()
    body_structure_ref.reference = resource_uuids['body_structure']

    body_structure_cod_ref = CodeableReference.construct()
    body_structure_cod_ref.reference = body_structure_ref
    body_structure_cod_ref.concept
    series.bodySite = body_structure_cod_ref

    mod_codeable = CodeableConcept.construct()
    mod_codeable.coding = list()
    mod_codeable.coding.append(
        {"system": "http://dicom.nema.org/resources/ontology/DCM", "code": "CT", "display": "Computed Tomography"})
    series.modality = mod_codeable
    study.series = [series]
    return study
