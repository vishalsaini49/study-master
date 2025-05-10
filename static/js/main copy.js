const App = (() => {
    const qs = (selector, parent = document) => parent.querySelector(selector);
    const qsa = (selector, parent = document) => [...parent.querySelectorAll(selector)];
  
    const Modal = {
      openStudentSelection(action) {
        const modal = qs("#student-selection-modal");
        if (!modal) return;
        modal.style.display = "flex";
        qsa(".student-row").forEach((row) => {
          row.addEventListener("click", () => {
            const studentId = row.dataset.id;
            if (action === "create-invoice") {
              window.location.href = `/students/${studentId}/create_invoice`;
            } else if (action === "receive-payment") {
              window.location.href = `/students/${studentId}/receive_payment`;
            }
          });
        });
      },
      closeModal(modalId) {
        const modal = qs(`#${modalId}`);
        if (modal) modal.style.display = "none";
      },
      openDeleteModal(type, id = null) {
        const modal = qs("#deleteModal");
        const form = qs("#deleteForm");
        const heading = qs("#modalHeading");
        const confirmBtn = qs("#confirmDeleteBtn");
  
        modal.style.display = "flex";
        heading.textContent = id
          ? "Confirm Delete"
          : "Delete Selected Users";
        form.action = id ? `/students/delete/${id}` : "/students/delete_bulk";
        confirmBtn.disabled = true;
      }
    };
  
    const Search = {
      filter(inputId, rowsSelector, fields) {
        const input = qs(inputId);
        if (!input) return;
  
        input.addEventListener("input", () => {
          const query = input.value.toLowerCase();
          qsa(rowsSelector).forEach((row) => {
            const matches = fields.some((field) =>
              row.dataset[field]?.toLowerCase().includes(query)
            );
            row.style.display = matches ? "" : "none";
          });
        });
      }
    };
  
    const Profile = {
      initUpdateToggle() {
        qsa(".profile-checkbox").forEach((checkbox) => {
          checkbox.addEventListener("change", () => {
            const inputId = checkbox.getAttribute("data-input");
            const input = qs(`#${inputId}`);
            if (input) input.disabled = !checkbox.checked;
          });
        });
      }
    };
  
    const Delete = {
      confirmDeleteInput() {
        const input = qs("#deleteConfirmInput");
        const confirmBtn = qs("#confirmDeleteBtn");
        if (!input || !confirmBtn) return;
  
        input.addEventListener("input", () => {
          confirmBtn.disabled = input.value !== "DELETE";
        });
      }
    };
  
    const Students = {
      addSubjectRow() {
        const container = qs("#subjectsContainer");
        const row = document.createElement("div");
        row.classList.add("subject-row", "grid", "grid-cols-2", "gap-2");
        row.innerHTML = `
          <input type="text" name="subjects[]" class="form-input" placeholder="Subject" required />
          <input type="number" name="fees[]" class="form-input" placeholder="Fee" required min="0" />
        `;
        container.appendChild(row);
      },
      removeSubjectRow() {
        const container = qs("#subjectsContainer");
        if (container.children.length > 1) {
          container.removeChild(container.lastChild);
        }
      },
      calculateTotalFees() {
        const feeInputs = qsa('input[name="fees[]"]');
        const total = feeInputs.reduce((sum, input) => sum + Number(input.value || 0), 0);
        const totalField = qs("#totalFees");
        if (totalField) totalField.value = total;
      }
    };
  
    const Invoice = {
      setupSubjectFeesSync() {
        const subjectRows = qsa(".subject-fee-row");
        const totalField = qs("#totalAmount");
        const paidField = qs("#amountPaid");
        const pendingField = qs("#pendingAmount");
  
        const updateTotals = () => {
          const total = subjectRows.reduce((sum, row) => {
            const fee = row.querySelector('input[name="fees[]"]');
            return sum + (Number(fee?.value || 0));
          }, 0);
          totalField.value = total;
          Invoice.updatePendingAmount();
        };
  
        subjectRows.forEach((row) => {
          const feeInput = row.querySelector('input[name="fees[]"]');
          feeInput.addEventListener("input", updateTotals);
        });
  
        paidField.addEventListener("input", Invoice.updatePendingAmount);
      },
      updatePendingAmount() {
        const total = Number(qs("#totalAmount")?.value || 0);
        const paid = Number(qs("#amountPaid")?.value || 0);
        const pending = total - paid;
        const pendingField = qs("#pendingAmount");
        if (!pendingField) return;
  
        pendingField.value = pending;
        pendingField.className = pending > 0 ? "text-red-500" : "text-green-500";
      },
      toggleInvoiceStatus() {
        qsa(".toggle-switch").forEach((toggle) => {
          toggle.addEventListener("click", async () => {
            const invoiceId = toggle.dataset.invoiceId;
            const response = await fetch(`/invoices/${invoiceId}/toggle_status`, { method: "POST" });
            const data = await response.json();
            toggle.textContent = data.new_status;
          });
        });
      }
    };
  
    const InputEffects = {
      setupFocusEffects() {
        qsa(".search-input").forEach((input) => {
          input.addEventListener("focus", () => {
            input.placeholder = "";
            input.classList.add("border-blue-500");
          });
          input.addEventListener("blur", () => {
            input.placeholder = "Search...";
            input.classList.remove("border-blue-500");
          });
        });
      }
    };
  
    // Public methods if needed elsewhere
    return {
      init: () => {
        Profile.initUpdateToggle();
        Delete.confirmDeleteInput();
        Search.filter("#studentSearch", ".student-row", ["name", "class", "contact"]);
        Search.filter("#invoiceSearch", ".invoice-row", ["name", "class", "contact"]);
        Invoice.setupSubjectFeesSync();
        Invoice.toggleInvoiceStatus();
        InputEffects.setupFocusEffects();
  
        // You can bind these to buttons like:
        // document.querySelector("#openDeleteModal").onclick = () => App.Modal.openDeleteModal();
      },
      Modal,
      Students,
      Invoice,
      Profile,
      Delete,
      Search,
    };
  })();
  
  document.addEventListener("DOMContentLoaded", App.init);  