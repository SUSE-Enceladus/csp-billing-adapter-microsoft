#
# spec file for package csp-billing-adapter-microsoft
#
# Copyright (c) 2023 SUSE LLC
#
# All modifications and additions to the file contributed by third parties
# remain the property of their copyright owners, unless otherwise agreed
# upon. The license for this file, and modifications and additions to the
# file, is the same license as for the pristine package itself (unless the
# license for the pristine package is not an Open Source License, in which
# case the license is the MIT License). An "Open Source License" is a
# license that conforms to the Open Source Definition (Version 1.9)
# published by the Open Source Initiative.

# Please submit bugfixes or comments via https://bugs.opensuse.org/
#


Name:           csp-billing-adapter-microsoft
Version:        0.0.1
Release:        0
Summary:        TBD
License:        Apache-2.0
URL:            https://github.com/SUSE-Enceladus/%{name}
Source:         https://files.pythonhosted.org/packages/source/c/%{name}/%{name}-%{version}.tar.gz
BuildRequires:  python-rpm-macros
BuildRequires:  python3-pluggy
BuildRequires:  python3-msal
BuildRequires:  python3-azure-identity
BuildRequires:  csp-billing-adapter
%if %{with test}
BuildRequires:  python3-pytest
BuildRequires:  python3-coverage
BuildRequires:  python3-pytest-cov
%endif
Requires:       python3-pluggy
Requires:       python3-msal
Requires:       python3-azure-identity
Requires:       csp-billing-adapter
BuildArch:      noarch

%description
TBD

%prep
%autosetup -n %{name}-%{version}

%build
%python_build

%install
%python_install
%python_expand %fdupes %{buildroot}%{$python_sitelib}

%check
%if %{with test}
python3 -m pytest --cov=csp_billing_adapter_microsoft
%endif

%files %{python_files}
%license LICENSE
%doc README.md CONTRIBUTING.md
%{python_sitelib}/%{name}
%{python_sitelib}/%{name}-%{version}*-info
%{_bindir}/%{name}

%changelog
