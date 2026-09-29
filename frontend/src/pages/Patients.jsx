import { useEffect, useState } from "react";
import {
  getPatients,
  createPatient,
  updatePatient,
  deletePatient as deletePatientRequest,
  getErrorMessage,
} from "../api/api";
function Patients() {

  const [patients, setPatients] = useState([]);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");

  const [showForm, setShowForm] = useState(false);

  const [editingPatient, setEditingPatient] = useState(null);

  const [form, setForm] = useState({
    full_name: "",
    age: "",
    gender: "",
    phone: "",
    address: "",
    disease: ""
  });


  // ==============================
  // LOAD PATIENTS
  // ==============================

  async function loadPatients() {

    try {

      setLoading(true);
      setError("");

     const response = await getPatients();

      setPatients(
        response.patients || []
      );

    } catch (error) {

      console.error(
        "Patients API error:",
        error
      );

      setError(
        getErrorMessage(error, "Unable to load patients.")
      );

    } finally {

      setLoading(false);

    }
  }


  useEffect(() => {

    loadPatients();

  }, []);


  // ==============================
  // FORM CHANGE
  // ==============================

  function handleChange(event) {

    const {
      name,
      value
    } = event.target;

    setForm((previous) => ({
      ...previous,
      [name]: value
    }));

  }


  // ==============================
  // OPEN ADD FORM
  // ==============================

  function openAddForm() {

    setEditingPatient(null);

    setForm({
      full_name: "",
      age: "",
      gender: "",
      phone: "",
      address: "",
      disease: ""
    });

    setShowForm(true);

  }


  // ==============================
  // OPEN EDIT FORM
  // ==============================

  function openEditForm(patient) {

    setEditingPatient(patient);

    setForm({
      full_name: patient.full_name || "",
      age: patient.age || "",
      gender: patient.gender || "",
      phone: patient.phone || "",
      address: patient.address || "",
      disease: patient.disease || ""
    });

    setShowForm(true);

  }


  // ==============================
  // SAVE PATIENT
  // ==============================

  async function handleSubmit(event) {

    event.preventDefault();

    try {

      const data = {
        full_name: form.full_name,
        age: Number(form.age),
        gender: form.gender,
        phone: form.phone,
        address: form.address,
        disease: form.disease || null
      };


      if (editingPatient) {

       await updatePatient(editingPatient.id, data);

      } else {

      await createPatient(data);
      }


      setShowForm(false);

      setEditingPatient(null);

      await loadPatients();

    } catch (error) {

      console.error(
        "Save patient error:",
        error
      );

      setError(
        getErrorMessage(error, "Unable to save patient.")
      );

    }

  }


  // ==============================
  // DELETE PATIENT
  // ==============================

  async function deletePatient(patientId) {

    const confirmed =
      window.confirm(
        "Are you sure you want to delete this patient?"
      );

    if (!confirmed) {
      return;
    }


    try {

      await deletePatientRequest(patientId);


      await loadPatients();

    } catch (error) {

      console.error(
        "Delete patient error:",
        error
      );

      setError(
        getErrorMessage(error, "Unable to delete patient.")
      );

    }

  }


  return (
    <div className="patients-page">

      {/* ==============================
          PAGE HEADER
      ============================== */}

      <div className="patients-header">

        <div>

          <h2>Patients</h2>

          <p>
            Manage patient information and records.
          </p>

        </div>


        <button
          className="primary-button"
          onClick={openAddForm}
        >
          + Add Patient
        </button>

      </div>


      {/* ==============================
          ERROR
      ============================== */}

      {error && (

        <div className="api-error">
          ⚠ {error}
        </div>

      )}


      {/* ==============================
          ADD / EDIT FORM
      ============================== */}

      {showForm && (

        <div className="patient-form-panel">

          <div className="panel-header">

            <div>

              <h3>
                {editingPatient
                  ? "Edit Patient"
                  : "Add New Patient"}
              </h3>

              <p>
                Enter the patient's information.
              </p>

            </div>

          </div>


          <form
            className="patient-form"
            onSubmit={handleSubmit}
          >

            <div className="form-grid">

              <div className="form-group">

                <label htmlFor="patient-full-name">
                  Full Name
                </label>

                <input
                  id="patient-full-name"
                  name="full_name"
                  value={form.full_name}
                  onChange={handleChange}
                  required
                  placeholder="Enter full name"
                />

              </div>


              <div className="form-group">

                <label htmlFor="patient-age">
                  Age
                </label>

                <input
                  id="patient-age"
                  type="number"
                  name="age"
                  value={form.age}
                  onChange={handleChange}
                  required
                  min="0"
                  placeholder="Enter age"
                />

              </div>


              <div className="form-group">

                <label htmlFor="patient-gender">
                  Gender
                </label>

                <select
                  id="patient-gender"
                  name="gender"
                  value={form.gender}
                  onChange={handleChange}
                  required
                >

                  <option value="">
                    Select gender
                  </option>

                  <option value="Male">
                    Male
                  </option>

                  <option value="Female">
                    Female
                  </option>

                  <option value="Other">
                    Other
                  </option>

                </select>

              </div>


              <div className="form-group">

                <label htmlFor="patient-phone">
                  Phone
                </label>

                <input
                  id="patient-phone"
                  name="phone"
                  value={form.phone}
                  onChange={handleChange}
                  required
                  placeholder="Enter phone number"
                />

              </div>


              <div className="form-group">

                <label htmlFor="patient-disease">
                  Disease
                </label>

                <input
                  id="patient-disease"
                  name="disease"
                  value={form.disease}
                  onChange={handleChange}
                  placeholder="Optional"
                />

              </div>


              <div className="form-group form-full">

                <label htmlFor="patient-address">
                  Address
                </label>

                <textarea
                  id="patient-address"
                  name="address"
                  value={form.address}
                  onChange={handleChange}
                  required
                  placeholder="Enter address"
                  rows="3"
                />

              </div>

            </div>


            <div className="form-actions">

              <button
                type="button"
                className="secondary-button"
                onClick={() => {
                  setShowForm(false);
                  setEditingPatient(null);
                }}
              >
                Cancel
              </button>

              <button
                type="submit"
                className="primary-button"
              >
                {editingPatient
                  ? "Update Patient"
                  : "Add Patient"}
              </button>

            </div>

          </form>

        </div>

      )}


      {/* ==============================
          PATIENT TABLE
      ============================== */}

      <div className="patients-panel">

        <div className="panel-header">

          <div>

            <h3>
              Patient Records
            </h3>

            <p>
              {patients.length} patient
              {patients.length !== 1 ? "s" : ""}
              {" "}found
            </p>

          </div>

        </div>


        {loading ? (

          <div className="empty-state">
            Loading patients...
          </div>

        ) : patients.length === 0 ? (

          <div className="empty-state">

            <h3>
              No patients found
            </h3>

            <p>
              Add your first patient to begin.
            </p>

          </div>

        ) : (

          <div className="patients-table-wrapper">

            <table className="patients-table">

              <thead>

                <tr>

                  <th>ID</th>

                  <th>Patient</th>

                  <th>Age</th>

                  <th>Gender</th>

                  <th>Phone</th>

                  <th>Disease</th>

                  <th>Actions</th>

                </tr>

              </thead>


              <tbody>

                {patients.map((patient) => (

                  <tr key={patient.id}>

                    <td data-label="ID">
                      #{String(patient.id).padStart(3, "0")}
                    </td>

                    <td data-label="Patient">
                      <strong>
                        {patient.full_name}
                      </strong>
                    </td>

                    <td data-label="Age">
                      {patient.age}
                    </td>

                    <td data-label="Gender">
                      {patient.gender}
                    </td>

                    <td data-label="Phone">
                      {patient.phone}
                    </td>

                    <td data-label="Disease">
                      {patient.disease || "—"}
                    </td>

                    <td data-label="Actions">

                      <button
                        className="table-edit-button"
                        onClick={() =>
                          openEditForm(patient)
                        }
                      >
                        Edit
                      </button>


                      <button
                        className="table-delete-button"
                        onClick={() =>
                          deletePatient(patient.id)
                        }
                      >
                        Delete
                      </button>

                    </td>

                  </tr>

                ))}

              </tbody>

            </table>

          </div>

        )}

      </div>

    </div>
  );
}

export default Patients;