// ---------- Base Logic ----------
(function handleStudentSelection() {
    const $ = selector => document.querySelector(selector);
    const $all = selector => document.querySelectorAll(selector);
    const items = $all(".student-item");
    const confirmBtn = $("#confirmSelection");
    let selectedStudentId = null;

    if (items.length && confirmBtn) {
        items.forEach(item => {
            item.addEventListener("click", () => {
                items.forEach(i => i.classList.remove("selected"));
                item.classList.add("selected");
                selectedStudentId = item.dataset.id;
                confirmBtn.disabled = false;
            });
        });

        confirmBtn.addEventListener("click", () => {
            if (selectedStudentId) {
                const action = confirmBtn.dataset.action;
                const source = confirmBtn.dataset.source || "invoices";  // fallback to invoices
        
                if (action === "create-invoice") {
                    window.location.href = `/create_invoice/${selectedStudentId}?source=${source}`;
                } else if (action === "receive-payment") {
                    window.location.href = `/receive_payment/${selectedStudentId}?source=${source}`;
                }
            }
        });
    }
})();

// ---------- Modal Back Button Logic ----------
document.addEventListener("DOMContentLoaded", () => {
    const studentModal = document.getElementById("studentSearchModal");
    const backButton = document.getElementById("backButton");

    if (studentModal && backButton) {
        studentModal.addEventListener("show.bs.modal", function (event) {
            const triggerButton = event.relatedTarget;
            const backUrl = triggerButton.getAttribute("data-back-url");
            backButton.href = backUrl || "/dashboard";
        });
    }
});

// ---------- Student Search ----------
(function searchFilter() {
    const inputStudent = document.querySelector("#studentsStudent");
    const inputInvoice = document.querySelector("#studentsInvoice");
    const tableStudent = document.querySelector("#tableStudent");
    const tableInvoice = document.querySelector("#tableInvoice");
  
    const attachSearch = (input, table) => {
      if (!input || !table) return;
  
      const rows = table.querySelectorAll("tbody tr");
  
      input.addEventListener("input", function () {
        const query = this.value.toLowerCase();
        rows.forEach(row => {
          const match = ["name", "class", "mobile", "subjects"]
            .some(attr => (row.dataset[attr] || "").includes(query));
          row.style.display = match ? "" : "none";
        });
      });
    };
  
    attachSearch(inputStudent, tableStudent);
    attachSearch(inputInvoice, tableInvoice);
  })();
  

// ---------- Update Profile ----------
(function toggleInputFields() {
    const $ = selector => document.querySelector(selector);
    const $all = selector => document.querySelectorAll(selector);
    $all('.toggle-input').forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            const fieldId = checkbox.id.replace('change', '').toLowerCase() + 'Field';
            const field = document.getElementById(fieldId);
            if (field) {
                field.classList.toggle('d-none', !checkbox.checked);
                if (!checkbox.checked) {
                    const input = field.querySelector('input, select');
                    if (input) input.value = '';
                }
            }
        });
    });
})();


// ---------- Students / Users Deletion ----------
(function globalDeletionModal() {
    const modal = document.getElementById("confirmModal");
    const deleteInput = document.getElementById("deleteConfirmInput");
    const deleteForm = document.getElementById("deleteForm");
    const deleteButton = document.getElementById("deleteButton");
    const selectedCount = document.getElementById("selectedCount");
    const entityName = document.getElementById("entityName");
    const entityType = document.getElementById("entityType");

    // 📦 1. Bulk or single student deletion (via checkboxes)
    document.querySelectorAll(".multi-delete-btn").forEach(btn => {
        btn.addEventListener("click", () => {
          const checked = document.querySelectorAll(".student-checkbox:checked");
          if (!checked.length) {
            return alert("Please select at least one student to delete.");
          }
      
          const selectedIds = Array.from(checked).map(cb => cb.value);
          openDeleteModal({
            type: "student",
            count: selectedIds.length,
            ids: selectedIds
          });
        });
      });

    // 🧍 2. Single user deletion (via delete button)
    document.querySelectorAll(".single-delete-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const id = btn.dataset.id;
            const type = btn.dataset.entity;

            if (!id || !type) {
                alert("Missing delete parameters.");
                return;
            }

            openDeleteModal({
                type: type,
                count: null,
                ids: [id]
            });
        });
    });

    // 🪄 3. Open modal
    window.openDeleteModal = ({ type = "item", count = null, ids = [] }) => {
        // Set hidden form values
        document.getElementById("entityTypeInput").value = type;
        document.getElementById("entityIdsInput").value = ids.join(',');

        // Reset input
        deleteInput.value = "";
        deleteButton.disabled = true;

        // Update modal content
        if (count !== null) {
            selectedCount.textContent = count;
            selectedCount.classList.remove("d-none");
            entityName?.classList.add("d-none");
        } else {
            entityName.textContent = type;
            entityName.classList.remove("d-none");
            selectedCount?.classList.add("d-none");
        }

        entityType.textContent = type;

        // Show modal
        modal.classList.remove("d-none");
    };

    // ❌ 4. Close modal
    window.closeModal = () => {
        modal.classList.add("d-none");
    };

    // ✍️ 5. Enable delete button when "DELETE" is typed
    deleteInput?.addEventListener("input", () => {
        deleteButton.disabled = deleteInput.value !== "DELETE";
    });
})();


// ---------- Add Student Page ----------
(function addStudentLogic() {
    const $ = selector => document.querySelector(selector);
    const $all = selector => document.querySelectorAll(selector);
    const container = $("#feesContainer");
    const totalDisplay = $("#totalFees");
    const checkboxes = $all('.subject-checkbox');

    if (!container || !totalDisplay || !checkboxes.length) return;

    function updateTotal() {
        let total = 0;
        $all('input[name^="fee["]').forEach(input => total += Number(input.value || 0));
        totalDisplay.textContent = total;
    }

    checkboxes.forEach(box => {
        box.addEventListener('change', () => {
            const subject = box.value;
            const rowId = `row-${subject}`;
            const existingRow = document.querySelector(`#${CSS.escape(rowId)}`);

            if (box.checked && !existingRow) {
                const row = document.createElement('tr');
                row.id = rowId;
                row.innerHTML = `
                    <td>${subject}</td>
                    <td><input type="number" name="fee[${subject}]" class="form-control" placeholder="Fees" required></td>
                    <td><input type="date" name="start[${subject}]" class="form-control" required></td>`;
                container.appendChild(row);

                 // 🆕 Prefill start date
                 const startInput = row.querySelector(`input[name="start[${CSS.escape(subject)}]"]`);
                 if (startInput) startInput.value = new Date().toISOString().split('T')[0];
                row.querySelector(`input[name="fee[${CSS.escape(subject)}]"]`)?.addEventListener('input', updateTotal);
            }

            if (!box.checked && existingRow) {
                existingRow.remove();
                updateTotal();
            }
        });
    });
})();

// ---------- Edit Student Page ----------
(function editStudentLogic() {
    const $ = selector => document.querySelector(selector);
    const $all = selector => Array.from(document.querySelectorAll(selector));
    const checkboxes = $all('.subject-checkbox');
    const totalDisplay = $("#totalFee");

    if (!checkboxes.length || !totalDisplay) return;

    function toggleFields(subject) {
        const fee = $(`input[name="fee[${subject}]"]`);
        const start = $(`input[name="start[${subject}]"]`);
        const isChecked = $(`input[name="subjects"][value="${subject}"]`)?.checked;

        [fee, start].forEach(field => {
            if (!field) return;
            field.disabled = !isChecked;
            if (isChecked && field === start && !start.value) {
                start.value = new Date().toISOString().split('T')[0];
            }
        });
    }

    function updateTotal() {
        let total = 0;
        checkboxes.forEach(cb => {
            if (cb.checked) {
                const fee = $(`input[name="fee[${cb.value}]"]`);
                if (fee) total += parseInt(fee.value || 0);
            }
        });
        totalDisplay.textContent = total;
    }

    checkboxes.forEach(cb => {
        toggleFields(cb.value);
        cb.addEventListener('change', () => {
            toggleFields(cb.value);
            updateTotal();
        });

        const fee = $(`input[name="fee[${cb.value}]"]`);
        if (fee) fee.addEventListener('input', updateTotal);
    });

    $("form")?.addEventListener('submit', e => {
        let valid = true;
        const checkedSubjects = checkboxes.filter(cb => cb.checked); // ✅ Now safe because $all returns Array
        // 🆕 Prevent empty submission
        if (checkedSubjects.length === 0) {
            e.preventDefault();
            alert('⚠️ Please select at least one subject.');
            return;
        }
        checkedSubjects.forEach(cb => {
            const fee = $(`input[name="fee[${cb.value}]"]`);
            const start = $(`input[name="start[${cb.value}]"]`);

            if (!fee.value || +fee.value <= 0) {
                fee.classList.add('border-danger', 'bg-danger', 'text-white');
                fee.addEventListener('input', () => {
                    fee.classList.remove('border-danger', 'bg-danger', 'text-white');
                });
                valid = false;
            }

            if (!start.value) {
                start.classList.add('border-danger', 'bg-danger', 'text-white');
                start.addEventListener('change', () => {
                    start.classList.remove('border-danger', 'bg-danger', 'text-white');
                });
                valid = false;
            }
        });

        if (!valid) {
            e.preventDefault();
            alert('⚠️ Please fill Fee & Start Date for all selected subjects.');
        }
    });

    updateTotal();
})();

// ---------- Create Invoice Page ----------
(function createInvoiceLogic() {
    const $ = selector => document.querySelector(selector);
    const $all = selector => document.querySelectorAll(selector);
    const invoiceData = document.getElementById('invoice-data');
    if (!invoiceData) return; // Don't run on pages that don't need it

    const studentSubjects = JSON.parse(invoiceData.dataset.studentSubjects || '{}');
    const invoiceSubjects = JSON.parse(invoiceData.dataset.invoiceSubjects || '{}');
    const subjectTable = $("#subjectTable tbody");
    const amountField = $("#invoiceAmount");
    const pendingField = $('input[name="pending"]');
    const amountReceivedField = $('input[name="amount_received"]');
    const invoiceToDate = document.querySelector('input[name="to_date"]')?.value || '';

    if (!subjectTable || !amountField || !pendingField || !amountReceivedField) return;

    function calculateTotal() {
        let total = 0;
        $all('input[name^="fee["]').forEach(input => total += +input.value || 0);
        amountField.value = total.toFixed(2);
        const received = +amountReceivedField.value || 0;
        const pending = total - received;
        pendingField.value = pending.toFixed(2);
        updatePendingColor(pending);
    }

    function updatePendingColor(pending) {
        pendingField.classList.remove('pending-green', 'pending-red');
        pendingField.classList.add(pending <= 0 ? 'pending-green' : 'pending-red');
    }

    function renderRow(subject, details = {}) {
        if (subjectTable.querySelector(`tr[data-subject="${CSS.escape(subject)}"]`)) return;
        const row = document.createElement('tr');
        row.dataset.subject = subject;
        row.innerHTML = `
            <td>${subject}</td>
            <td><input type="number" class="form-control" name="fee[${subject}]" value="${details.fee || ''}" required></td>
            <td><input type="date" class="form-control" name="start_date[${subject}]" value="${details.start_date || ''}" required></td>
            <td><input type="date" class="form-control" name="received_till[${subject}]" value="${details.received_till || invoiceToDate}" required></td>
        `;
        subjectTable.appendChild(row);
        row.querySelector(`input[name="fee[${subject}]"]`).addEventListener('input', calculateTotal);
        calculateTotal();
    }

    $all('.subject-checkbox').forEach(box => {
        const subject = box.value;
        box.addEventListener('change', () => {
            if (box.checked) {
                const details = invoiceSubjects[subject] || studentSubjects[subject] || {};
                renderRow(subject, details);
            } else {
                subjectTable.querySelector(`tr[data-subject="${CSS.escape(subject)}"]`)?.remove();
                calculateTotal();
            }
        });
        if (box.checked) {
            console.log("invoiceSubjects keys:", Object.keys(invoiceSubjects));
            console.log("studentSubjects keys:", Object.keys(studentSubjects));
            
            console.log("Toggled:", subject);
            console.log("From invoiceSubjects:", invoiceSubjects[subject]);
            console.log("From studentSubjects:", studentSubjects[subject]);

            const details = invoiceSubjects[subject] || studentSubjects[subject] || {};
            renderRow(subject, details);
        }
    });

    if (!amountReceivedField.value) amountReceivedField.value = '0';
    amountReceivedField.addEventListener('input', calculateTotal);

    calculateTotal();
})();


// Student Search box
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.querySelector('.search-input');
    const defaultPlaceholder = searchInput.getAttribute('placeholder');
    const inputWrapper = document.querySelector('.input-wrapper');
    const searchContainer = document.querySelector('.search-container');
  
    searchInput.addEventListener('focus', () => {
      searchInput.setAttribute('placeholder', '');
      inputWrapper.classList.add('focused');
      searchContainer.classList.add('focused');
    });
  
    searchInput.addEventListener('blur', () => {
      searchInput.setAttribute('placeholder', defaultPlaceholder);
      inputWrapper.classList.remove('focused');
      searchContainer.classList.remove('focused');
    });
  });
  function clearSearch(event) {
    const searchInput = document.querySelector('.search-input');
    const clearBtn = event.currentTarget;
  
    searchInput.value = '';
    searchInput.dispatchEvent(new Event('input')); // Re-trigger filtering logic
    clearBtn.focus(); // This removes focus from input
  
    setTimeout(() => clearBtn.blur(), 100); // Optional: remove button focus after
  }
  